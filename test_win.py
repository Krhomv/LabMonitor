import flet as ft
import threading
import time
import asyncio

def main(page: ft.Page):
    print("page.window attributes:", [attr for attr in dir(page.window) if not attr.startswith('_')])
    
    async def kill():
        await asyncio.sleep(1)
        await page.window.destroy_async() if hasattr(page.window, 'destroy_async') else None
    
    if hasattr(page, 'run_task'):
        page.run_task(kill)

ft.app(target=main)
