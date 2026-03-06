from __future__ import annotations

import random
from datetime import datetime

from mid.blocks.base import BaseBlock, BlockRender


QUOTES = [
    (
        "La simplicidad es la máxima sofisticación.",
        "Leonardo da Vinci",
    ),
    (
        "Lo que no se mide, no se puede mejorar.",
        "Peter Drucker",
    ),
    (
        "La acción es la clave fundamental de todo éxito.",
        "Pablo Picasso",
    ),
    (
        "La estrategia sin táctica es el camino más lento hacia la victoria.",
        "Sun Tzu",
    ),
]


class QuoteBlock(BaseBlock):
    id = "quote"
    title = "Nota del día"
    description = "Frase inspiradora"
    refresh_seconds = 45
    col_span = 4
    row_span = 3
    col = 9
    row = 1
    order = 30

    def render(self) -> BlockRender:
        quote, author = random.choice(QUOTES)
        now = datetime.now().astimezone().strftime("%d %b %Y")
        html = f"""
        <div class="block-header">
            <h2 class="block-title">{self.title}</h2>
            <span class="block-tag">{now}</span>
        </div>
        <div class="block-body quote-body">
            <p class="quote-text">“{quote}”</p>
            <p class="quote-author">— {author}</p>
        </div>
        """.strip()
        return BlockRender(html=html, refresh_seconds=self.refresh_seconds)
