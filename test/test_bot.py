import numpy as np
import pandas as pd
import pytest

from bot import dati, strategie
from bot.backtest import Costi, compra_e_tieni, esegui
from bot.carta import Conto
from bot.indicatori import atr, donchian, rsi, zscore
from bot.rischio import Bloccato, Guardia, Limiti
from bot.validazione import deflaziona, permutazione, scegli, sharpe_da_rumore, walk_forward


@pytest.fixture(scope="module")
def df():
    return dati.Sintetico().serie()


# --- dati ---------------------------------------------------------------

def test_serie_coerente(df):
    assert (df["massimo"] >= df["minimo"]).all()
    assert df.index.is_monotonic_increasing and df.index.tz is not None


def test_csv_rifiuta_colonne_mancanti(tmp_path):
    f = tmp_path / "x.csv"
    pd.DataFrame({"pippo": range(400)},
                 index=pd.date_range("2020", periods=400)).to_csv(f)
    with pytest.raises(dati.DatiInsufficienti):
        dati.da_csv(f)


def test_rifiuta_serie_troppo_corta(tmp_path):
    f = tmp_path / "y.csv"
    pd.DataFrame({"open": [1.0]*10, "high": [1.0]*10, "low": [1.0]*10,
                  "close": [1.0]*10, "volume": [1.0]*10},
                 index=pd.date_range("2020", periods=10)).to_csv(f)
    with pytest.raises(dati.DatiInsufficienti):
        dati.da_csv(f)


# --- indicatori ---------------------------------------------------------

def test_rsi_in_range(df):
    assert rsi(df["chiusura"]).dropna().between(0, 100).all()


def test_atr_positivo(df):
    assert (atr(df).dropna() > 0).all()


def test_zscore_centrato(df):
    z = zscore(df["chiusura"], 20).dropna()
    assert abs(z.mean()) < 1.0 and z.std() > 0


def test_donchian_esclude_la_barra_corrente(df):
    alto, _ = donchian(df, 20)
    # il massimo a 20 giorni non deve mai contenere il massimo di oggi
    assert (alto.dropna() == df["massimo"].rolling(20).max().shift(1).dropna()).all()


# --- strategie ----------------------------------------------------------

@pytest.mark.parametrize("s", strategie.TUTTE, ids=[s.nome for s in strategie.TUTTE])
def test_segnale_in_zero_uno(df, s):
    sig = s.segnale(df, next(s.combinazioni()))
    assert sig.between(0.0, 1.0).all() and len(sig) == len(df)


@pytest.mark.parametrize("s", strategie.TUTTE, ids=[s.nome for s in strategie.TUTTE])
def test_nessuno_sguardo_al_futuro(df, s):
    """Cambiare SOLO l'ultima barra non deve toccare nessun segnale precedente.
    È il test che smaschera il lookahead, ed è il più importante del file."""
    par = next(s.combinazioni())
    a = s.segnale(df, par)
    d2 = df.copy()
    for c in ("apertura", "massimo", "minimo", "chiusura"):
        d2.iloc[-1, d2.columns.get_loc(c)] *= 3
    b = s.segnale(d2, par)
    pd.testing.assert_series_equal(a.iloc[:-1], b.iloc[:-1])


def test_griglie_non_vuote():
    for s in strategie.TUTTE:
        assert s.n_combinazioni == len(list(s.combinazioni())) >= 1


def test_dimensione_sotto_il_tetto(df):
    p = strategie.dimensiona(strategie.TREND.segnale(df, {"veloce": 20, "lenta": 100}),
                             df, massimo=0.8)
    assert p.max() <= 0.8 + 1e-12 and p.min() >= 0.0


# --- backtest -----------------------------------------------------------

def test_esecuzione_sfasata_di_una_barra(df):
    """Posizione che entra solo all'ultima barra: non deve produrre rendimento."""
    pos = pd.Series(0.0, index=df.index)
    pos.iloc[-1] = 1.0
    eq, e = esegui(df, pos, Costi(0, 0))
    assert eq.iloc[-1] == pytest.approx(1.0)


def test_compra_e_tieni_uguale_al_prezzo(df):
    eq, _ = compra_e_tieni(df)
    atteso = df["chiusura"].iloc[-1] / df["chiusura"].iloc[0]
    assert eq.iloc[-1] == pytest.approx(atteso, rel=1e-9)


def test_i_costi_tolgono(df):
    pos = strategie.dimensiona(strategie.TREND.segnale(df, {"veloce": 20, "lenta": 100}), df)
    _, senza = esegui(df, pos, Costi(0, 0))
    _, con = esegui(df, pos, Costi(0.001, 0.001))
    assert con.sharpe < senza.sharpe and con.costi > 0


def test_posizione_nulla_non_rende(df):
    eq, e = esegui(df, pd.Series(0.0, index=df.index))
    assert eq.iloc[-1] == pytest.approx(1.0) and e.dentro == 0.0


# --- validazione --------------------------------------------------------

def test_walk_forward_non_vede_il_futuro(df):
    """I parametri della finestra k non devono dipendere da dati oltre la finestra."""
    eq, fin, e = walk_forward(strategie.TREND, df, barre_is=756, barre_oos=126)
    assert len(fin) >= 2
    d2 = df.copy()
    d2.iloc[-1, d2.columns.get_loc("chiusura")] *= 5
    _, fin2, _ = walk_forward(strategie.TREND, d2, barre_is=756, barre_oos=126)
    assert [f.parametri for f in fin[:-1]] == [f.parametri for f in fin2[:-1]]


def test_scegli_resta_nella_griglia(df):
    par, _ = scegli(strategie.BREAKOUT, df, Costi())
    assert par in list(strategie.BREAKOUT.combinazioni())


def test_permutazione_restituisce_p_valido(df):
    r = permutazione(strategie.TREND, df, {"veloce": 20, "lenta": 100}, n=40)
    assert 0.0 <= r["p"] <= 1.0 and r["n"] == 40


def test_rumore_cresce_con_le_prove():
    assert sharpe_da_rumore(200, 1000) > sharpe_da_rumore(10, 1000) > 0
    assert sharpe_da_rumore(1, 1000) == 0.0


def test_deflazione_penalizza():
    assert deflaziona(1.5, 200, 1000) < deflaziona(1.5, 10, 1000) < 1.5


# --- rischio e carta ----------------------------------------------------

def test_guardia_taglia_leva():
    assert Guardia(Limiti(esposizione_massima=1.0)).filtra(3.0) == 1.0


def test_guardia_ferma_su_drawdown():
    g = Guardia(Limiti(drawdown_stop=0.1))
    g.aggiorna(1.0, 0.0)
    g.aggiorna(0.85, -0.15)
    with pytest.raises(Bloccato):
        g.filtra(0.5)


def test_guardia_azzera_dopo_perdita_giornaliera():
    g = Guardia(Limiti(perdita_giornaliera=0.03))
    g.aggiorna(1.0, -0.04)
    assert g.filtra(1.0) == 0.0


def test_conto_ignora_micro_ordini():
    c = Conto(contante=1000.0)
    c.segna(100.0)
    assert c.porta_a(0.001, 100.0) is None


def test_conto_arriva_al_peso():
    c = Conto(contante=1000.0)
    c.porta_a(0.5, 100.0, costo_lato=0.0)
    assert c.quantita * 100.0 == pytest.approx(500.0, rel=1e-6)
    assert c.contante == pytest.approx(500.0, rel=1e-6)


def test_conto_non_invia_ordini_veri():
    """Il modulo non deve contenere nessuna chiamata di rete: è un conto di carta."""
    import inspect
    from bot import carta
    src = inspect.getsource(carta)
    for vietato in ("requests", "http", "urllib", "ccxt", "api_key", "socket"):
        assert vietato not in src.lower()


# --- avvisi e giro ------------------------------------------------------

def test_avvisi_senza_token_non_esplode(monkeypatch, capsys):
    from bot import avvisi
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert avvisi.configurato() is False
    assert avvisi.manda("ciao") is False
    assert "ciao" in capsys.readouterr().out


def test_avvisi_nessun_segreto_nel_sorgente():
    import inspect
    from bot import avvisi
    src = inspect.getsource(avvisi)
    assert "TELEGRAM_TOKEN" in src
    # nessun token letterale: i token Telegram hanno la forma cifre:lettere
    import re
    assert not re.search(r"\b\d{8,}:[A-Za-z0-9_-]{30,}", src)


def test_avvisi_tronca_messaggi_lunghi():
    from bot.avvisi import LIMITE, _tronca
    assert len(_tronca("x" * 99999)) == LIMITE


def test_freccia_copre_i_casi():
    from bot.giro import _freccia
    assert _freccia(0.0, 1.0) == "ENTRA"
    assert _freccia(1.0, 0.0) == "ESCE"
    assert _freccia(0.5, 0.9) == "AUMENTA"
    assert _freccia(0.9, 0.5) == "RIDUCE"
    assert _freccia(0.5, 0.5) == "FERMO"


def test_stato_scritto_in_modo_atomico(tmp_path, monkeypatch):
    from bot import giro
    monkeypatch.setattr(giro, "STATO", tmp_path / "stato.json")
    giro._salva_stato({"a": 1})
    assert giro._stato() == {"a": 1}
    assert not (tmp_path / "stato.tmp").exists()


def test_stato_corrotto_non_blocca(tmp_path, monkeypatch):
    from bot import giro
    f = tmp_path / "stato.json"
    f.write_text("{ non json")
    monkeypatch.setattr(giro, "STATO", f)
    assert giro._stato() == {}


def test_messaggio_dichiara_che_e_carta():
    from bot.giro import Decisione, messaggio
    d = Decisione("SPY", "2026-10-16", 700.0, 1.0, 0.0, {"veloce": 20}, "trend", "ENTRA")
    m = messaggio(d)
    assert "nessun ordine reale" in m and "SPY" in m and "ENTRA" in m


# --- output a terminale -------------------------------------------------

CP = "cp1252"   # la codifica della console italiana di Windows


def _stringhe_nei_print(modulo: str) -> list:
    """Ogni stringa costante che finisce dentro una print() del modulo."""
    import ast
    import io
    albero = ast.parse(io.open(modulo, encoding="utf-8").read())
    trovate = []
    for n in ast.walk(albero):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print":
            for s in ast.walk(n):
                if isinstance(s, ast.Constant) and isinstance(s.value, str):
                    trovate.append(s.value)
    return trovate


@pytest.mark.parametrize("modulo", ["bot/cli.py", "bot/__main__.py", "misura.py"])
def test_print_codificabili_su_console_windows(modulo):
    """Un carattere fuori cp1252 in una print fa esplodere il programma."""
    for s in _stringhe_nei_print(modulo):
        s.encode(CP)


def test_riassunto_codificabile_su_console_windows(tmp_path, monkeypatch):
    """riassunto() va su Telegram ma anche in console: deve restare stampabile."""
    import json
    from bot import giro
    d = tmp_path / "diario.jsonl"
    riga = {"quando": pd.Timestamp.now(tz="UTC").isoformat(), "data": "2026-10-16",
            "simbolo": "SPY", "motivo": "ENTRA", "peso_prima": 0.0, "peso": 1.0}
    d.write_text(json.dumps(riga) + "\n", encoding="utf-8")
    monkeypatch.setattr(giro, "DIARIO", d)
    giro.riassunto(7).encode(CP)


def test_fallback_console_non_esplode_su_cp1252(monkeypatch):
    """Senza token manda() stampa il messaggio: non deve morire sull'encoding."""
    import io
    import sys
    from bot import avvisi
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding=CP))
    assert avvisi.manda("⚠️ SPY 0% → 100%") is False
