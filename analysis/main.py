#! /app/analysis/venv/bin python

import socketio
import asyncio
import json
from typing import Any

import socketio.async_client
import socketio.exceptions
from commFunc.analysis import analysis_data
from commFunc.process import process_data
from db_connector import MySQLConnector


async def get_socketio_connector():
    sio = socketio.async_client.AsyncClient(reconnection=False)

    @sio.event
    async def connect():

        print('connect')

    @sio.event()
    async def disconnect():
        print("disconnect")
        raise ConnectionRefusedError

    @sio.on('sendEcg', namespace="/Ecg")
    async def on_message(data):
        global user
        # print(data["eq"])
        user = await process_data(user, data)

        if len(user[data["eq"]]["body"]) >= 300:
            if not user[data["eq"]]["analysis_in_progress"]:
                user[data["eq"]]["analysis_in_progress"] = True
                try:
                    result = await analysis_data(user, data["eq"])
                    dbResult = await send_to_db(result, conn)

                    if dbResult:
                        backup_path = './backup_data.json'
                        await send_to_db(result, conn_backup, backup_path)

                        user[data["eq"]]["body"] = user[data["eq"]]["body"][300:]
                        print(f"user len : {len(user[data['eq']]['body'])}")

                finally:
                    user[data["eq"]]["analysis_in_progress"] = False

    return sio


# MySQL 커넥터 생성
conn = MySQLConnector(
    host="host",
    user="user",
    password="password",
    db="db",
    port=port
)

conn_backup = MySQLConnector(
    host="host",
    user="user",
    password="password",
    db="db",
    port=port
)

user = {}
namespace = "/Ecg"


async def send_to_db(data: dict, conn: Any, backup_path: str = None) -> int:
    sql = (
        "insert into ecg_stress (eq, sDate, eDate, timezone, mean_RR_ms, "
        "std_RR_SDNN_ms, min_HR_beats_min, max_HR_beats_min, rmssd_ms, nn50, pnn50, "
        "apen, srd, tsrd, vlf_ms2, lf_ms2, hf_ms2, tp_ms2) value (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")

    input_data = (
        data["eq"],
        data["sDate"],
        data["eDate"],
        data["timezone"],
        data['Mean RR (ms)'],
        data["STD RR/SDNN (ms)"],
        data["Min HR (beats/min)"],
        data["Max HR (beats/min)"],
        data["RMSSD (ms)"],
        data["NN50"],
        data["pNN50 (%)"],
        data["apen"],
        data["srd"],
        data["tsrd"],
        data["vlf (ms2)"],
        data["lf (ms2)"],
        data["hf (ms2)"],
        data["tp (ms2)"])

    return await conn.execute_query(sql, input_data, data, backup_path)

# WebSocket 서버에 연결하는 함수


async def connect_to_websocket() -> None:
    global user
    sio = await get_socketio_connector()
    while True:
        print("connect to Socket.IO")
        try:
            await sio.connect('wss://', namespaces=namespace)
            print("Connected to Socket.IO server")
            print("emit pythonRoom")
            await sio.emit(event="pythonRoom", data="pythonEcg", namespace=namespace)
            print("emit_complete")

            await sio.wait()

        except Exception as e:
            print(f"Connection failed. Retrying after 2 seconds.")
            sio.connected = False
            await asyncio.sleep(2)


# 비동기 루프 실행
asyncio.run(connect_to_websocket())
