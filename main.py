import socketio
from loguru import logger

import uvicorn
from fastapi import FastAPI

from src.models.user import User
from src.models.message import Message

ROOMS = ['lobby', 'general', 'random']

# Заставляем работать пути к статике
static_files = {'/': 'static/index.html', '/static': './static'}
sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
app = FastAPI()
socket_app = socketio.ASGIApp(sio, app, static_files)


# настройки логирования
logger.remove()
# Базовый лог
logger.debug("Это сообщение уровня DEBUG")
logger.info("Это информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
logger.critical("Критическая ошибка")

logger.add(
    "loggs.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="5 MB",  # Ротация файла каждые 10 MB
    retention="10 days",  # Хранить только 5 последних логов
    compression="zip",  # Сжимать старые логи в архив
    backtrace=True,     # Сохранение трассировки ошибок
    diagnose=True       # Подробный вывод
)


clients_dict = {}
rooms_dict = {}


# Обрабатываем подключение пользователя
@sio.event
async def connect(sid, environ):
    logger.info(f"Пользователь {sid} подключился")


# Отправляем комнаты
@sio.on('get_rooms')
async def on_get_rooms(sid, data):
    rooms = list(rooms_dict)
    await sio.emit("rooms", data={"rooms": ROOMS}, to=sid)


@sio.on('join')
async def on_join(sid, data):
    global clients_dict, rooms_dict
    user = User(room=data["room"], name=data["name"], messages=[])
    clients_dict[f'{sid}'] = {"name": user.name, "room": user.room, "messages": user.messages}
    rooms_dict[user.room] = {sid:{'name': user.name}}
    await sio.save_session(sid, session={"name": user.name, "room": user.room})
    await sio.emit("move", data={"room": user.room}, to=sid)
    await sio.enter_room(sid, user.room)




@sio.on('leave')
async def on_leave(sid, data):
    session = await sio.get_session(sid)
    await sio.leave_room(sid, session.get("room"))
    del rooms_dict[session.get("room")][sid]
    session['room'] = None
    await sio.save_session(sid, session)



# Обрабатываем отправку ответа
@sio.on('send_message')
async def on_message(sid, data):
    session = await sio.get_session(sid)
    message = Message(text=data["text"], author=session.get("name"))
    await sio.emit('message', data={"name": message.author, "text": message.text}, room=session.get('room'))


@sio.on('message')
async def messages(sid, data):
    message = Message(text=data["text"], author=data("name"))
    clients_dict[sid]['messages'].append(message.text)

# Обрабатываем отключение пользователя
@sio.event
async def disconnect(sid):
    logger.info(f"Пользователь {sid} отключился")


if __name__ == '__main__':
    uvicorn.run(socket_app, host='0.0.0.0', port=8000)
    rooms_dict["lobby"] = {}
    rooms_dict["general"] = {}
    rooms_dict["random"] = {}
