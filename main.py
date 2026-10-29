import os
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("O Globo Play")

SITE = "https://oglobo.globo.com"
FONTES_PLAY = [
    "https://oglobo.globo.com/play/",
    "https://oglobo.globo.com/play/novelas/",
]


def obter_pagina(url: str) -> BeautifulSoup:
    with httpx.Client(
        timeout=25,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        },
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


@mcp.tool()
def buscar_noticias(termo: str = "") -> str:
    """Busca notícias na seção Play do jornal O Globo, incluindo novelas e TV.
    Pode filtrar os títulos por uma palavra ou assunto."""
    try:
        resultados = []
        vistos = set()
        erros = []

        for fonte in FONTES_PLAY:
            try:
                soup = obter_pagina(fonte)
            except Exception as e:
                erros.append(f"{fonte}: {type(e).__name__}")
                continue

            for link in soup.find_all("a", href=True):
                titulo = link.get_text(" ", strip=True)
                url = urljoin(fonte, link["href"])
                parsed = urlparse(url)

                if parsed.scheme != "https" or parsed.hostname != "oglobo.globo.com":
                    continue

                # Mantém a busca dentro da seção Play, sem misturar notícias gerais.
                if not parsed.path.startswith("/play/"):
                    continue

                if not titulo or len(titulo) < 15 or url in vistos:
                    continue

                if termo and termo.casefold() not in titulo.casefold():
                    continue

                vistos.add(url)
                resultados.append(f"- {titulo}\n  Link: {url}")

                if len(resultados) >= 20:
                    break

            if len(resultados) >= 20:
                break

        if not resultados:
            detalhe = (
                " Não foi possível acessar as páginas consultadas: "
                + "; ".join(erros)
                if erros
                else " Confira se a seção publicou matérias acessíveis no momento."
            )
            return (
                "Não encontrei matérias correspondentes na seção Play do O Globo."
                + detalhe
            )

        return "Matérias encontradas na seção Play do O Globo:\n\n" + "\n\n".join(resultados)

    except Exception as e:
        return f"Erro ao buscar matérias do Play: {type(e).__name__}: {e}"


@mcp.tool()
def ler_noticia(url: str) -> str:
    """Lê o título e o texto disponível de uma matéria pública do O Globo."""
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "oglobo.globo.com"
        or not parsed.path.startswith("/play/")
    ):
        return (
            "Informe uma URL HTTPS de uma matéria da seção Play, "
            "por exemplo: https://oglobo.globo.com/play/novelas/..."
        )

    try:
        soup = obter_pagina(url)

        for item in soup(["script", "style", "nav", "footer", "header"]):
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
        return f"Erro ao ler a matéria: {type(e).__name__}: {e}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
    )
