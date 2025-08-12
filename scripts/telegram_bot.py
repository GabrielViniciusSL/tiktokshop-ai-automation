import os, json, html
from dataclasses import dataclass, asdict
from typing import List, Dict
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv

# ---------- bootstrap ----------
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CONFIG_PATH = Path("configs/config.json")
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

# states simples para o fluxo de busca
ASK_TERM = "ASK_TERM"
ASK_STOCK = "ASK_STOCK"

# ---------- modelos de config ----------
@dataclass
class GlobalCfg:
    vpd: int = 3          # vídeos por dia
    avg_views: int = 5000 # views/vídeo
    ctr: float = 0.04     # 4%
    conv: float = 0.02    # 2%
    margin: float = 0.30  # 30%
    days: int = 30        # horizonte (dias)

@dataclass
class State:
    global_cfg: GlobalCfg
    per_sku: Dict[str, Dict]  # overrides por SKU

def load_state() -> State:
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        gc = GlobalCfg(**data.get("global_cfg", {}))
        per = data.get("per_sku", {})
        return State(global_cfg=gc, per_sku=per)
    return State(global_cfg=GlobalCfg(), per_sku={})

def save_state(st: State):
    payload = {"global_cfg": asdict(st.global_cfg), "per_sku": st.per_sku}
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

STATE = load_state()

# ---------- mock de catálogo (trocaremos por API) ----------
CATALOG: List[Dict] = [
    {"sku": "EL-TRIMPRO", "name": "Aparador Pro 5-em-1", "stock": 520, "price": 129.90},
    {"sku": "HM-STEAMX", "name": "Vaporizador Portátil X", "stock": 140, "price": 189.00},
    {"sku": "KT-AIRFRY", "name": "AirFryer Mini 2L",       "stock": 980, "price": 249.00},
    {"sku": "SP-GLUTES", "name": "Elástico Glúteos Pro",   "stock": 85,  "price": 69.90 },
    {"sku": "PT-LINTGO", "name": "Removedor de Fiapos",    "stock": 360, "price": 79.90 },
]

# ---------- helpers ----------
def esc(s: str) -> str:
    return html.escape(str(s), quote=False)

def fmt_money(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def cfg_for_sku(sku: str) -> GlobalCfg:
    override = STATE.per_sku.get(sku.upper(), {})
    base = STATE.global_cfg
    return GlobalCfg(
        vpd=override.get("vpd", base.vpd),
        avg_views=override.get("avg_views", base.avg_views),
        ctr=override.get("ctr", base.ctr),
        conv=override.get("conv", base.conv),
        margin=override.get("margin", base.margin),
        days=override.get("days", base.days),
    )

def calc_product_roi(p: Dict) -> Dict:
    sku = p["sku"].upper()
    cfg = cfg_for_sku(sku)
    monthly_views = cfg.vpd * cfg.avg_views * cfg.days
    clicks = monthly_views * cfg.ctr
    predicted_sales = int(round(clicks * cfg.conv))
    cap_sales = min(p["stock"], predicted_sales)
    gross = cap_sales * p["price"]
    profit = gross * cfg.margin
    return {
        "sku": sku, "name": p["name"], "stock": p["stock"],
        "predicted_sales": predicted_sales, "cap_sales": cap_sales,
        "gross": gross, "profit": profit, "cfg": cfg
    }

def rank_products(catalog: List[Dict]) -> List[Dict]:
    scored = [calc_product_roi(p) for p in catalog]
    scored.sort(key=lambda s: (s["profit"], s["cap_sales"], s["stock"]), reverse=True)
    return scored

def pct(x: float) -> str:
    return f"{x*100:.1f}%"

def fmt_cfg(cfg: GlobalCfg) -> str:
    return (f"vpd={cfg.vpd} | avg_views={cfg.avg_views} | "
            f"ctr={pct(cfg.ctr)} | conv={pct(cfg.conv)} | "
            f"margin={pct(cfg.margin)} | days={cfg.days}")

def parse_kv(text: str) -> Dict:
    out = {}
    if not text:
        return out
    for chunk in text.replace("\n", " ").split(","):
        if "=" in chunk:
            k, v = chunk.strip().split("=", 1)
            k = k.strip().lower()
            v = v.strip().lower().replace("%", "")
            try:
                if k in {"vpd", "avg_views", "days"}:
                    out[k] = int(float(v))
                elif k in {"ctr", "conv", "margin"}:
                    val = float(v)
                    out[k] = val/100 if val > 1 else val
            except:
                pass
    return out

def _matches(p: Dict, term: str) -> bool:
    t = term.lower()
    return t in p["sku"].lower() or t in p["name"].lower()

# ---------- bot handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📈 Pesquisar Produtos (ROI+Estoque)", callback_data='search_flow')],
        [InlineKeyboardButton("🎬 Gerar Vídeo", callback_data='generate')],
        [InlineKeyboardButton("🚀 Postar no TikTok", callback_data='post')],
        [InlineKeyboardButton("📊 Ver Métricas", callback_data='metrics')]
    ]
    await update.message.reply_text(
        "Bem-vindo ao TikTokShop AI Bot. Escolha uma opção:\n"
        "Comandos: /search termo  |  /showconfig  |  /config  |  /configsku",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# fluxo interativo: term -> stock_min -> resultado
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == 'search_flow':
        context.user_data[ASK_TERM] = True
        context.user_data.pop(ASK_STOCK, None)
        await q.edit_message_text(
            text="🧭 Digite a <b>palavra‑chave ou categoria</b> para filtrar produtos:",
            parse_mode="HTML"
        )
        return

    elif q.data == 'generate':
        await q.edit_message_text(text="🎬 Gerando vídeo de <b>teste</b>… (placeholder)", parse_mode="HTML")

    elif q.data == 'post':
        await q.edit_message_text(text="🚀 Preparando postagem no TikTok… (placeholder)", parse_mode="HTML")

    elif q.data == 'metrics':
        await q.edit_message_text(text="📊 Métricas mock: Views=5.000 | CTR=4% | Conv=2% | ROI=positivo (placeholder)", parse_mode="HTML")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gerencia as etapas do fluxo interativo de busca."""
    msg = (update.message.text or "").strip()

    # 1) receber termo
    if context.user_data.get(ASK_TERM):
        context.user_data["term"] = msg
        context.user_data.pop(ASK_TERM, None)
        context.user_data[ASK_STOCK] = True
        await update.message.reply_text(
            "📦 Estoque mínimo para considerar? (ex.: 100)\n"
            "Dica: envie um número inteiro.",
            parse_mode="HTML"
        )
        return

    # 2) receber estoque mínimo
    if context.user_data.get(ASK_STOCK):
        try:
            stock_min = int(float(msg))
        except ValueError:
            await update.message.reply_text("Valor inválido. Envie um número, ex.: <b>100</b>.", parse_mode="HTML")
            return

        term = context.user_data.get("term", "")
        context.user_data.pop(ASK_STOCK, None)

        subset = [p for p in CATALOG if _matches(p, term) and p["stock"] >= stock_min]
        if not subset:
            await update.message.reply_text(
                f"🔎 Nada encontrado para <b>{esc(term)}</b> com estoque ≥ <b>{stock_min}</b>.",
                parse_mode="HTML"
            )
            return

        ranked = rank_products(subset)[:10]
        lines = [f"<b>🔍 Resultados</b> para “{esc(term)}” com estoque ≥ {stock_min}"]
        for i, s in enumerate(ranked, 1):
            cfg = s["cfg"]
            flag = "⚠️" if s["stock"] < s["predicted_sales"] else "✅"
            lines.append(
                f"<b>{i}.</b> {esc(s['name'])} ({esc(s['sku'])})\n"
                f"  Estoque: {s['stock']} {flag} | Prev.: {s['predicted_sales']} | Cap.: {s['cap_sales']}\n"
                f"  Faturamento: {esc(fmt_money(s['gross']))} | Lucro: {esc(fmt_money(s['profit']))}\n"
                f"  CFG: vpd={cfg.vpd} | avg_views={cfg.avg_views} | ctr={cfg.ctr:.2%} | conv={cfg.conv:.2%} | margin={cfg.margin:.2%} | days={cfg.days}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")
        return

    # fallback: se mandar texto fora do fluxo, sugira o /search direto
    if msg.startswith("/"):
        return  # outros comandos serão tratados pelos handlers
    await update.message.reply_text("Use o menu ou o comando /search termo.", parse_mode="HTML")

# comandos utilitários
async def cmd_showconfig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = STATE.global_cfg
    msg = ("🧩 <b>Config Global Atual</b>\n" +
           esc(fmt_cfg(cfg)) +
           "\n\n<b>Overrides por SKU:</b>\n" +
           esc(", ".join(STATE.per_sku.keys()) if STATE.per_sku else "—"))
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    kv = parse_kv(args)
    if not kv:
        await update.message.reply_text(
            "Use: <code>/config vpd=3, avg_views=6000, ctr=0.04, conv=0.02, margin=0.30, days=30</code>\n"
            "Valores de % aceitam <code>0.05</code> ou <code>5%</code>.",
            parse_mode="HTML")
        return
    for k, v in kv.items():
        setattr(STATE.global_cfg, k, v)
    save_state(STATE)
    await update.message.reply_text("✅ Config global atualizada:\n" + esc(fmt_cfg(STATE.global_cfg)), parse_mode="HTML")

async def cmd_configsku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use: <code>/configsku EL-TRIMPRO vpd=4, avg_views=7000, ctr=0.05</code>\n"
            "Remover override: <code>/configsku EL-TRIMPRO clear</code>",
            parse_mode="HTML")
        return
    sku = context.args[0].upper()
    if len(context.args) == 2 and context.args[1].lower() == "clear":
        STATE.per_sku.pop(sku, None)
        save_state(STATE)
        await update.message.reply_text(f"♻️ Overrides removidos para {esc(sku)}.", parse_mode="HTML")
        return
    kv = parse_kv(" ".join(context.args[1:]))
    if not kv:
        await update.message.reply_text("Nenhuma chave válida. Ex.: <code>ctr=0.05, conv=0.02</code>", parse_mode="HTML")
        return
    STATE.per_sku[sku] = {**STATE.per_sku.get(sku, {}), **kv}
    save_state(STATE)
    await update.message.reply_text(f"✅ Override salvo para {esc(sku)}: {esc(STATE.per_sku[sku])}", parse_mode="HTML")

# comando /search (rápido)
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Use: <code>/search airfryer</code> ou <code>/search vaporizador</code>",
            parse_mode="HTML")
        return
    term = " ".join(context.args)
    subset = [p for p in CATALOG if _matches(p, term)]
    if not subset:
        await update.message.reply_text(f"🔎 Nada encontrado para <b>{esc(term)}</b>.", parse_mode="HTML")
        return
    ranked = rank_products(subset)[:10]
    lines = [f"<b>🔍 Resultados</b> para “{esc(term)}”"]
    for i, s in enumerate(ranked, 1):
        cfg = s["cfg"]
        flag = "⚠️" if s["stock"] < s["predicted_sales"] else "✅"
        lines.append(
            f"<b>{i}.</b> {esc(s['name'])} ({esc(s['sku'])})\n"
            f"  Estoque: {s['stock']} {flag} | Prev.: {s['predicted_sales']} | Cap.: {s['cap_sales']}\n"
            f"  Faturamento: {esc(fmt_money(s['gross']))} | Lucro: {esc(fmt_money(s['profit']))}\n"
            f"  CFG: vpd={cfg.vpd} | avg_views={cfg.avg_views} | ctr={cfg.ctr:.2%} | conv={cfg.conv:.2%} | margin={cfg.margin:.2%} | days={cfg.days}"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

def main():
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN ausente no .env")
    app = ApplicationBuilder().token(TOKEN).build()

    # comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("showconfig", cmd_showconfig))
    app.add_handler(CommandHandler("config", cmd_config))
    app.add_handler(CommandHandler("configsku", cmd_configsku))
    app.add_handler(CommandHandler("search", cmd_search))

    # botões do menu (inclui entrada do fluxo interativo)
    app.add_handler(CallbackQueryHandler(button))

    # handler de texto para o fluxo de busca (term -> stock)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == '__main__':
    main()




