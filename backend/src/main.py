from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import chess
import os
import uuid
from typing import Dict

app = FastAPI()

# Получаем абсолютный путь к директории static
static_path = os.path.join(os.path.dirname(__file__), '../static')
templates_path = os.path.join(os.path.dirname(__file__), '../templates')

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Словарь для хранения игр
games: Dict[str, dict] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, game_id: str, color: str):
        await websocket.accept()
        if game_id not in self.active_connections:
            self.active_connections[game_id] = {}
        self.active_connections[game_id][color] = websocket

    def disconnect(self, game_id: str, color: str):
        if game_id in self.active_connections:
            self.active_connections[game_id].pop(color, None)
            if not self.active_connections[game_id]:
                self.active_connections.pop(game_id, None)

    async def broadcast_move(self, game_id: str, data: dict):
        if game_id in self.active_connections:
            for connection in self.active_connections[game_id].values():
                await connection.send_json(data)

manager = ConnectionManager()

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )

@app.post("/create_game")
async def create_game():
    game_id = str(uuid.uuid4())
    games[game_id] = {
        "board": chess.Board(),
        "white": None,
        "black": None
    }
    return {"game_id": game_id}

@app.get("/game/{game_id}")
async def game(request: Request, game_id: str, color: str = None):
    if game_id not in games:
        return RedirectResponse(url="/")
    
    if not color:
        # Автоматически назначаем цвет новому игроку
        if not games[game_id]["white"]:
            color = "white"
            games[game_id]["white"] = True
        elif not games[game_id]["black"]:
            color = "black"
            games[game_id]["black"] = True
        else:
            return RedirectResponse(url="/")  # Игра уже заполнена
    
    return templates.TemplateResponse(
        "game.html",
        {
            "request": request,
            "game_id": game_id,
            "color": color
        }
    )

@app.websocket("/ws/{game_id}/{color}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, color: str):
    await manager.connect(websocket, game_id, color)
    try:
        while True:
            data = await websocket.receive_json()
            if game_id in games:
                board = games[game_id]["board"]
                
                from_pos = data["from"]
                to_pos = data["to"]
                
                # Преобразуем координаты
                from_row = int(from_pos[0])
                from_col = int(from_pos[1])
                to_row = int(to_pos[0])
                to_col = int(to_pos[1])
                
                from_square = chess.square(from_col, 7 - from_row)
                to_square = chess.square(to_col, 7 - to_row)
                
                # Проверяем ход пешки
                piece = board.piece_at(from_square)
                is_promotion = (piece is not None and 
                              piece.piece_type == chess.PAWN and 
                              ((piece.color == chess.WHITE and to_row == 0) or 
                               (piece.color == chess.BLACK and to_row == 7)))
                
                if is_promotion:
                    move = chess.Move(from_square, to_square, promotion=chess.QUEEN)
                else:
                    move = chess.Move(from_square, to_square)
                
                if move in board.legal_moves:
                    board.push(move)
                    await manager.broadcast_move(game_id, {
                        "status": "success",
                        "move": {
                            "from": from_pos,
                            "to": to_pos,
                            "promotion": is_promotion
                        }
                    })
                else:
                    await websocket.send_json({
                        "status": "error",
                        "message": "Невалидный ход"
                    })
                    
    except WebSocketDisconnect:
        manager.disconnect(game_id, color)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
