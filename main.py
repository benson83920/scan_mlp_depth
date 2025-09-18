import ccxt.pro as ccxt
import asyncio
import os
from dotenv import load_dotenv
import requests
import pytz
from datetime import datetime
import logging

load_dotenv()

# 設定時區為 GMT+8
tz_GMT8 = pytz.timezone("Asia/Taipei")

# 取得當前月份和日期（格式：MM_DD HH:mm:ss）
current_date = datetime.now(tz_GMT8).strftime("%m_%d_%H_%M_%S")

# 取得專案資料夾的絕對路徑
log_folder = "/app/logs"  # 確保這裡指向容器內的 logs 目錄
# log_folder = "./"
log_filename = os.path.join(log_folder, f"{current_date}_start_time_GMT8.log")


class GMT8Formatter(logging.Formatter):
    """自訂 Formatter，強制所有時間顯示為 GMT+8"""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=pytz.utc).astimezone(tz_GMT8)
        return dt.strftime(datefmt if datefmt else "%Y-%m-%d %H:%M:%S")


# 設定日誌格式與輸出到檔案
formatter = GMT8Formatter("%(asctime)s - %(levelname)s - %(message)s")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_filename,
    filemode="a",
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger = logging.getLogger()
logger.handlers.clear()  # 清除預設 handler，確保只有 GMT+8 格式的 handler
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def send_telegram_message(message):
    chat_id = os.getenv("CHAT_ID")
    bot_token = os.getenv("BOT_TOKEN")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={message}"

    response = requests.get(url)


async def main():

    symbol = "MLP/USDT"
    limit = 500

    gate = ccxt.gateio()

    while True:
        try:
            orderbooks = await gate.fetch_order_book(symbol, limit=50)
            ticker = await gate.fetch_ticker(symbol)
            close = ticker["close"]
            bids = orderbooks["bids"]
            asks = orderbooks["asks"]

            upper_bound = close * 1.02
            lower_bound = close * 0.98

            # 計算買單深度（bids）
            bids_depth = sum(
                [
                    amount
                    for price, amount in bids
                    if lower_bound <= price <= upper_bound
                ]
            )
            # 計算賣單深度（asks）
            asks_depth = sum(
                [
                    amount
                    for price, amount in asks
                    if lower_bound <= price <= upper_bound
                ]
            )

            bids_depth_USDT = bids_depth * close
            asks_depth_USDT = asks_depth * close

            if bids_depth_USDT < limit:
                message = (
                    f"買單深度不足\n"
                    f"買單深度低於 {limit} USDT！\n"
                    f"需要補上: {(limit - bids_depth_USDT):2f} USDT\n"
                    f"往下補到價格：{lower_bound:7f} 就好\n"
                    f"最新價格: {close} USDT\n"
                    f"買單深度(USDT): {bids_depth_USDT:2f} USDT\n"
                    f"賣單深度(USDT): {asks_depth_USDT:2f} USDT\n"
                )
                send_telegram_message(message)
                logging.info(message)
                logging.info(f"買單 --- SEND ---")

            if asks_depth_USDT < limit:
                message = (
                    f"賣單深度不足\n"
                    f"賣單深度低於 {limit} USDT！\n"
                    f"需要補上: {(limit - asks_depth_USDT):2f} USDT\n"
                    f"往上補到價格：{upper_bound:7f} 就好\n"
                    f"最新價格: {close} USDT\n"
                    f"買單深度(USDT): {bids_depth_USDT:2f} USDT\n"
                    f"賣單深度(USDT): {asks_depth_USDT:2f} USDT\n"
                )
                send_telegram_message(message)
                logging.info(message)
                logging.info(f"賣單 --- IGNORE ---")

            if bids_depth_USDT < limit or asks_depth_USDT < limit:
                send_telegram_message("我給你「2分鐘」時間補單，不補我就再叫一次")
                logging.info("我給你「2分鐘」時間補單，不補我就再叫一次")
                await asyncio.sleep(120)

            await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Error loading markets: {e}")
            continue


if __name__ == "__main__":
    asyncio.run(main())
