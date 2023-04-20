from fastapi import FastAPI
from app_filemanager.api import api

app = FastAPI()

app.include_router(api)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', reload=True)
