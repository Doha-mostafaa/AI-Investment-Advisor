import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
    PG_PORT = int(os.getenv("POSTGRES_PORT", 5433))
    PG_DB = os.getenv("POSTGRES_DB", "copilot")
    PG_USER = os.getenv("POSTGRES_USER", "copilot")
    PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "copilot")

    @property
    def pg_dsn(self):
        return f"postgresql+psycopg2://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
    FMP_API_KEY = os.getenv("FMP_API_KEY", "")
    SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "CopilotDemo demo@example.com")

    TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "MCD",
               "NVDA", "TSLA", "JPM", "KO", "XOM"]

    DOSSIER_REFRESH_HOURS = int(os.getenv("DOSSIER_REFRESH_HOURS", 1))
    PRICES_REFRESH_MINUTES = int(os.getenv("PRICES_REFRESH_MINUTES", 60))
    NEWS_REFRESH_MINUTES = int(os.getenv("NEWS_REFRESH_MINUTES", 30))

config = Config()