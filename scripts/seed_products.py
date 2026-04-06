from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from init_db import init_db
from models.model_products import create_product, get_product_by_id, update_product


PRODUCTS = [
    {
        "id": "jade",
        "name": "Jade DIY",
        "summary": "Carteira de hardware open-source, segura e flexível.",
        "details_html": """
<h4>Documentação do Dispositivo JADE DIY</h4>
<p><strong>Introdução:</strong> dispositivo seguro e transparente.</p>
<p><strong>Por que hardware open source?</strong> <a href="https://plebs.substack.com/p/hard-wallets-seguras" target="_blank">Artigo</a></p>
<p><strong>Conectividade:</strong> GreenWallet • SideSwap • Sparrow • Electrum</p>
<p><strong>Atualizações:</strong> via navegador / binários Sandmann / compilação GitHub</p>
<p><strong>Bateria:</strong> interna (indicação limitada)</p>
<p><strong>Segurança:</strong> Secure-element virtual Oracle</p>
<p>Tutorial: <a href="https://www.youtube.com/watch?v=k-maFZiKSw4" target="_blank">YouTube</a></p>
<p><a href="https://docs.google.com/document/d/1Bf8O-R478woq8z7Z8DnN9XlfGf9B3GT8rn0qgJiAUHM/edit?usp=sharing" target="_blank">Documentação completa</a></p>
""".strip(),
        "images": [
            "images/jade1.png",
            "images/jade2.png",
            "images/jade3.png",
            "images/jade4.png",
            "images/jade5.png",
            "images/jade6.png",
            "images/jade7.png",
            "images/jade8.png",
            "images/jade9.png",
        ],
        "prices": [
            {"label": "Jade DIY", "amount_sats": 0, "display_text": "R$ 230"},
            {"label": "Box de Proteção", "amount_sats": 0, "display_text": "R$ 70"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Jade DIY",
                "inputs": [
                    {"name": "jadeColor", "label": "Case"},
                    {"name": "buttonColor", "label": "Botões"},
                ],
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção",
                "inputs": [
                    {"name": "boxColor", "label": "Box"},
                    {"name": "handleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Jade DIY",
        "badge_text": "Promo",
        "badge_variant": "promo",
        "sort_order": 0,
        "active": True,
    },
    {
        "id": "pico",
        "name": "PicoFido / PicoKey (RP2040 • FIDO2)",
        "summary": "Chave de segurança FIDO-U2F / FIDO2 baseada no RP2040 (USB-C).",
        "details_html": """
<h4>Detalhes Técnicos</h4>
<p>• Projeto 100% open-source — código, esquemas e guias em <a href="https://github.com/polhenarejos/pico-fido" target="_blank">github.com/polhenarejos/pico-fido</a>.</p>
<p>• Compatível: Google, Proton Mail, Microsoft Outlook, GitHub, X/Twitter…</p>
<p>• FIDO2 dispensa SMS/app 2FA; chaves ficam no dispositivo.</p>
<p>• USB-C fêmea; alimentação do host (cabo não incluído).</p>
<p>• Conectividade: Android • Linux • Windows (iOS/macOS não testados).</p>
<p>• <a href="https://docs.google.com/document/d/1JIE_6lNlFsk-TwPceDngePEg8G9fe3FKINjHCGeSUgg/edit?usp=drive_link" target="_blank">Documentação completa</a>.</p>
""".strip(),
        "images": [
            "images/pico1.png",
            "images/pico2.png",
            "images/pico3.png",
        ],
        "prices": [
            {"label": "PicoFido / PicoKey", "amount_sats": 0, "display_text": "R$ 159"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores",
                "inputs": [
                    {"name": "picoBodyColor", "label": "Corpo"},
                    {"name": "picoRingColor", "label": "Anel"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar PicoFido",
        "badge_text": "Novo",
        "badge_variant": "new",
        "sort_order": 1,
        "active": True,
    },
    {
        "id": "nerd",
        "name": "NerdMiner — CASE (sem bateria)",
        "summary": "CASE para NerdMiner (TTGO T-Display). *Não inclui bateria nem placa.",
        "details_html": """
<p>• ~55 KH/s (info do projeto) • Stratum / pools self-custody.<br>
• Firmware: <a href="https://github.com/BitMaker-hub/NerdMiner_v2" target="_blank">GitHub</a>.<br>
• USB-C 5 V • Tutorial: <a href="https://www.youtube.com/watch?v=Cq0y1034oq8" target="_blank">YouTube</a>.</p>
<p><strong>TTGO T-Display:</strong> <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">Comprar no AliExpress</a></p>
<p><em>APENAS CASE — sem bateria.</em></p>
""".strip(),
        "images": [
            "images/nm1.png",
            "images/nm2.png",
            "images/nm3.png",
        ],
        "prices": [
            {"label": "Case TTGO T-Display", "amount_sats": 0, "display_text": "R$ 70"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores do Case",
                "inputs": [
                    {"name": "nerdCaseColor", "label": "Case"},
                    {"name": "nerdButtonColor", "label": "Botões"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar NerdMiner",
        "badge_text": "Case",
        "badge_variant": "neutral",
        "sort_order": 2,
        "active": True,
    },
    {
        "id": "sandseed",
        "name": "SandSeed – placas para backup de seed",
        "summary": "Kit Stakbit 1248 – 5 placas (3 lisas + 2 perfuradas) padrão BIP-39.",
        "details_html": """
<p><strong>Como usar:</strong> sobre base firme, perfure cada letra (estilete, agulha grossa ou punção).</p>
<p><strong>Utilidade:</strong> gravação física, offline e resistente ao fogo/água das 24 palavras da seed BIP-39.</p>
<p>Tutorial: <a href="https://stackbit.me/tutorial-stackbit-1248/" target="_blank">Vídeo oficial (Stackbit)</a></p>
<p style="font-size:.9rem;color:#ccc">
  Design original por <a href="https://twitter.com/valandro" target="_blank">@Valandro</a>.
  Versão em aço inox na <a href="https://stackbit.me/tutorial-stackbit-1248/#loja" target="_blank">loja do autor</a>.
</p>
""".strip(),
        "images": [
            "images/sandseed1.png",
            "images/sandseed2.png",
        ],
        "prices": [
            {"label": "Placa avulsa", "amount_sats": 2000, "display_text": "2 000 sats"},
            {"label": "Kit 5 un", "amount_sats": 5000, "display_text": "5 000 sats"},
        ],
        "options": [
            {"type": "seedPack"},
        ],
        "allow_addon_seed": False,
        "buy_button_text": "Comprar SandSeed",
        "badge_text": "Sats",
        "badge_variant": "neutral",
        "sort_order": 3,
        "active": True,
    },
    {
        "id": "krux",
        "name": "Krux Yahboom Modcase (c/ bateria)",
        "summary": "Modcase com bateria; placa eletrônica não inclusa.",
        "details_html": """
<h4>Detalhes Técnicos</h4>
<p>Inclui bateria e box de proteção (placa não inclusa).</p>
<p>Tutorial: <a href="https://www.youtube.com/watch?v=V48RpmuZEwI" target="_blank">YouTube</a></p>
<p>Placa referência Yahboom: <a href="https://de.aliexpress.com/item/1005005585064305.html" target="_blank">AliExpress</a></p>
<p>Documentação: <a href="https://docs.google.com/document/d/1s70HUmdX3XX08GbINxEAay5eK_D3c4RLReKuautZYB4/edit?usp=sharing" target="_blank">Google Docs</a></p>
<p>Encomenda completa: ~25 dias • R$ 775 + R$ 89 (box)</p>
""".strip(),
        "images": [
            "images/krux1.png",
            "images/krux2.png",
            "images/krux3.png",
            "images/krux4.png",
        ],
        "prices": [
            {"label": "Modcase", "amount_sats": 0, "display_text": "R$ 250"},
            {"label": "Box de Proteção", "amount_sats": 0, "display_text": "R$ 89"},
        ],
        "options": [
            {
                "type": "colorSingle",
                "title": "Modcase (opcional)",
                "input": {"name": "kruxColor", "label": "Modcase"},
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção (opcional)",
                "inputs": [
                    {"name": "kruxBoxColor", "label": "Box"},
                    {"name": "kruxHandleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Modcase",
        "badge_text": None,
        "badge_variant": None,
        "sort_order": 4,
        "active": True,
    },
    {
        "id": "kruxcase",
        "name": "Krux Yahboom Case (impressão 3D)",
        "summary": "Somente impressão 3D do case. Compatível com placas Krux Yahboom.",
        "details_html": """
<p>Impressão 3D em PLA/ASA sob encomenda. Não inclui eletrônica.</p>
""".strip(),
        "images": [
            "images/kruxcase1.png",
            "images/kruxcase2.png",
            "images/kruxcase3.png",
        ],
        "prices": [
            {"label": "Case", "amount_sats": 0, "display_text": "R$ 90"},
        ],
        "options": [
            {
                "type": "colorSingle",
                "title": "Case",
                "input": {"name": "kruxCaseColor", "label": "Case"},
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção (opcional)",
                "inputs": [
                    {"name": "kruxCaseBoxColor", "label": "Box"},
                    {"name": "kruxCaseHandleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Case",
        "badge_text": "3D",
        "badge_variant": "neutral",
        "sort_order": 5,
        "active": True,
    },
    {
        "id": "ttgo-case-bateria",
        "name": "Case TTGO T-Display (com bateria)",
        "summary": "Case para TTGO T-Display com bateria integrada. *Não inclui a placa.",
        "details_html": """
<p><strong>Compatibilidade:</strong> TTGO T-Display.</p>
<p><strong>Observação:</strong> produto se refere apenas ao <em>case</em>; a placa TTGO não está inclusa.</p>
<p><strong>TTGO T-Display (referência):</strong> <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a></p>
<p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
""".strip(),
        "images": [
            "images/jadecase2.png",
            "images/jadecase3.png",
            "images/jadecase7.png",
            "images/jade9.png",
        ],
        "prices": [
            {"label": "Case c/ bateria", "amount_sats": 0, "display_text": "R$ 120"},
            {"label": "Box de Proteção", "amount_sats": 0, "display_text": "R$ 70"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores do Case",
                "inputs": [
                    {"name": "ttgoCaseColor", "label": "Case"},
                    {"name": "ttgoButtonColor", "label": "Botões"},
                ],
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção (opcional)",
                "inputs": [
                    {"name": "ttgoBoxColor", "label": "Box"},
                    {"name": "ttgoHandleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Case (c/ bateria)",
        "badge_text": "Novo",
        "badge_variant": "new",
        "sort_order": 6,
        "active": True,
    },
    {
        "id": "jade-diy-sem-bateria",
        "name": "Jade DIY (TTGO T-Display, sem bateria)",
        "summary": "Case para Jade DIY sem bateria integrada. *Não inclui a placa.",
        "details_html": """
<p><strong>Compatibilidade:</strong> TTGO T-Display (Jade DIY).</p>
<p><strong>Observação:</strong> produto se refere apenas ao <em>case</em> sem bateria; a placa TTGO não está inclusa.</p>
<p><strong>TTGO T-Display (referência):</strong> <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a></p>
<p><strong>Documentação Jade DIY:</strong> <a href="https://docs.google.com/document/d/1Bf8O-R478woq8z7Z8DnN9XlfGf9B3GT8rn0qgJiAUHM/edit?usp=sharing" target="_blank">Google Docs</a></p>
<p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
""".strip(),
        "images": [
            "images/jade2.png",
            "images/jade3.png",
            "images/jade7.png",
            "images/jade9.png",
        ],
        "prices": [
            {"label": "Jade DIY (sem bateria)", "amount_sats": 0, "display_text": "R$ 150"},
            {"label": "Box de Proteção", "amount_sats": 0, "display_text": "R$ 70"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores do Case",
                "inputs": [
                    {"name": "jadeNoBatCaseColor", "label": "Case"},
                    {"name": "jadeNoBatButtonColor", "label": "Botões"},
                ],
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção (opcional)",
                "inputs": [
                    {"name": "jadeNoBatBoxColor", "label": "Box"},
                    {"name": "jadeNoBatHandleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Jade DIY (sem bateria)",
        "badge_text": "Econômico",
        "badge_variant": "neutral",
        "sort_order": 7,
        "active": True,
    },
    {
        "id": "ttgo-case-sem-bateria",
        "name": "TTGO T-Display — Case (sem bateria)",
        "summary": "Case para TTGO T-Display SEM bateria integrada. *Não inclui a placa.",
        "details_html": """
<p><strong>Compatibilidade:</strong> TTGO T-Display.</p>
<p><strong>Observação:</strong> produto refere-se apenas ao <em>case</em> sem bateria; a placa TTGO não está inclusa.</p>
<p><strong>TTGO T-Display (referência de compra):</strong> <a href="https://pt.aliexpress.com/item/1005005970553639.html?channel=twinner" target="_blank">AliExpress</a></p>
<p><strong>Montagem (vídeo):</strong> <a href="https://youtu.be/S5LI_bG9f1U" target="_blank">YouTube</a></p>
""".strip(),
        "images": [
            "images/jade2.png",
            "images/jade3.png",
            "images/jade7.png",
            "images/jade9.png",
        ],
        "prices": [
            {"label": "Case sem bateria", "amount_sats": 0, "display_text": "R$ 70"},
            {"label": "Box de Proteção", "amount_sats": 0, "display_text": "R$ 70"},
        ],
        "options": [
            {
                "type": "colorPair",
                "title": "Cores do Case",
                "inputs": [
                    {"name": "ttgoNoBatCaseColor", "label": "Case"},
                    {"name": "ttgoNoBatButtonColor", "label": "Botões"},
                ],
            },
            {
                "type": "colorPair",
                "title": "Box de Proteção (opcional)",
                "inputs": [
                    {"name": "ttgoNoBatBoxColor", "label": "Box"},
                    {"name": "ttgoNoBatHandleColor", "label": "Alças"},
                ],
            },
        ],
        "allow_addon_seed": True,
        "buy_button_text": "Comprar Case (sem bateria)",
        "badge_text": "Sem bateria",
        "badge_variant": "neutral",
        "sort_order": 8,
        "active": True,
    },
]


def seed_products():
    init_db()
    for product in PRODUCTS:
        if get_product_by_id(product["id"]):
            update_product(product["id"], product)
        else:
            create_product(product)


if __name__ == "__main__":
    seed_products()
    print(f"Seeded {len(PRODUCTS)} products.")
