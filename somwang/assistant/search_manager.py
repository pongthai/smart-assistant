
# assistant/search_manager.py

import requests
from bs4 import BeautifulSoup
from .config import SERPER_API_KEY
from .logger_config import get_logger

logger = get_logger(__name__)

class SearchManager:
    def __init__(self):
        logger.info("SearchManager initialized")
        self.serper_api_key = SERPER_API_KEY

    def search_serper(self, query, top_k=5):
        
        logger.debug("Enter search_serper")
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key
        }
        payload = {"q": query}

        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()

        results = data.get("organic", [])[:top_k]
        logger.debug("Exit search_perper")
        return results

    def fetch_webpage_content(self, url):
        try:
            logger.debug("Enter fetch_webpage_content")
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            text = "\n".join(p.get_text() for p in paragraphs)
            logger.debug("Exit fetch_webpage_content")
            return text.strip()
        except Exception as e:
            logger.error(f"❌ Error fetching {url}: {e}")
            return ""
    def build_context_from_search_results(self, results):
        logger.debug("Enter build_context_from_search_results")
        context_parts = []

        for idx, item in enumerate(results, 1):
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            link = item.get('link', '')

            if not title and not snippet:
                continue

            # 🔥 ลอง fetch เนื้อหาจากหน้าเว็บจริง
            page_content = self.fetch_webpage_content(link)

            # 🔥 เอาแค่ย่อหน้าแรกพอ ไม่งั้น context ยาวเกิน
            if page_content:
                page_content = page_content.split("\n")[0][:500]  # ตัดที่ 500 ตัวอักษรแรก

    #        context_entry = f"""
    #{idx}. {title}
    #{snippet}
    #Link: {link}
    #Extracted Content: {page_content if page_content else 'N/A'}
    #""".strip()
            context_entry = f"""
    {idx}. {title}:
    {snippet}    
    Extracted Content: {page_content if page_content else 'N/A'}
    """.strip()

            context_parts.append(context_entry)

        logger.debug("Exit build_context_from_search_results")
        return "\n\n".join(context_parts).strip()

    # def build_context_from_search_results(self, results):
    #     context_parts = []

    #     for idx, item in enumerate(results, 1):
    #         title = item.get('title', '')
    #         snippet = item.get('snippet', '')
    #         link = item.get('link', '')

    #         if not title and not snippet:
    #             continue

    #         context_entry = f"{idx}. {title}\n{snippet}\nLink: {link}"
    #         context_parts.append(context_entry)

    #     return "\n\n".join(context_parts).strip()