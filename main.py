
import os
import re
import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("O Globo Play")

@mcp.tool()
def ler_noticia(url: str) -> str:
    """Lê o título e o texto de uma notícia pública do O Globo Play."""
    if not url.startswith("https://oglobo.globo.com/"):
        return "Informe uma URL HTTPS do site oglobo.globo.com."

    try:
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for item in soup(["script", "style", "nav", "footer", "header"]):
            item.decompose()

        title = soup.find("h1")
        title_text = title.get_text(" ", strip=True) if title else "Título não encontrado"

        article = soup.find("article") or soup
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in article.find_all("p")
            if p.get_text(" ", strip=True)
        ]

        text = "\n".join(paragraphs)
        text = re.sub(r"\n{3,}", "\n\n", text)

        if not text:
            return f"Título: {title_text}\nNão foi possível extrair o texto da notícia."

        return f"Título: {title_text}\n\n{text[:12000]}"

    except Exception as e:
        return f"Erro ao ler a notícia: {type(e).__name__}: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port
    )
