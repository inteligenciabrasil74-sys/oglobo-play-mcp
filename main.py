
import os
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("O Globo Play")

SITE = "https://oglobo.globo.com/"


def obter_pagina(url: str) -> BeautifulSoup:
    with httpx.Client(
        timeout=25,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


@mcp.tool()
def buscar_noticias(termo: str = "") -> str:
    """Busca títulos e links de notícias na página inicial do O Globo.
    Pode filtrar os títulos por uma palavra ou assunto."""
    try:
        soup = obter_pagina(SITE)
        resultados = []
        vistos = set()

        for link in soup.find_all("a", href=True):
            titulo = link.get_text(" ", strip=True)
            url = urljoin(SITE, link["href"])
            parsed = urlparse(url)

            if parsed.netloc not in (
                "oglobo.globo.com",
                "www.oglobo.globo.com"
            ):
                continue

            if not titulo or len(titulo) < 25:
                continue

            if parsed.path == "/" or url in vistos:
                continue

            if termo and termo.casefold() not in titulo.casefold():
                continue

            vistos.add(url)
            resultados.append(f"- {titulo}\n  Link: {url}")

            if len(resultados) >= 15:
                break

        if not resultados:
            return (
                "Não encontrei notícias correspondentes na página inicial. "
                "O site pode ter alterado sua estrutura ou bloqueado o acesso."
            )

        return "Notícias encontradas:\n\n" + "\n\n".join(resultados)

    except Exception as e:
        return f"Erro ao buscar notícias: {type(e).__name__}: {e}"


@mcp.tool()
def ler_noticia(url: str) -> str:
    """Lê o título e o texto disponível de uma notícia pública do O Globo."""
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname not in (
            "oglobo.globo.com",
            "www.oglobo.globo.com"
        )
    ):
        return "Informe uma URL HTTPS válida do oglobo.globo.com."

    try:
        soup = obter_pagina(url)

        for item in soup(
            ["script", "style", "nav", "footer", "header"]
        ):
            item.decompose()

        title = soup.find("h1")
        title_text = (
            title.get_text(" ", strip=True)
            if title
            else "Título não encontrado"
        )

        article = soup.find("article") or soup
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in article.find_all("p")
            if p.get_text(" ", strip=True)
        ]

        text = "\n".join(paragraphs)
        text = re.sub(r"\n{3,}", "\n\n", text)

        if not text:
            return (
                f"Título: {title_text}\n"
                "Não foi possível extrair o texto. "
                "A matéria pode exigir assinatura ou bloquear o acesso."
            )

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
