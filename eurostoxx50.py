from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import io
import os
import smtplib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

today_str = datetime.now().strftime("%d %B %Y")

indices = {
	"Euro Stoxx 50": "^STOXX50E",
	"DAX (Germany)": "^GDAXI",
	"CAC 40 (France)": "^FCHI",
	"FTSE 100 (UK)": "^FTSE",
	"SMI (Switzerland)": "^SSMI",
	"AEX (Netherlands)": "^AEX",
	"IBEX 35 (Spain)": "^IBEX",
	"FTSE MIB (Italy)": "FTSEMIB.MI",
}

euro_stoxx_50_dict = {
	"ASML.AS": "ASML Holding", "MC.PA": "LVMH", "SAP.DE": "SAP SE",
	"SIE.DE": "Siemens AG", "ALV.DE": "Allianz SE", "SAN.MC": "Banco Santander",
	"BBVA.MC": "BBVA", "TTE.PA": "TotalEnergies", "IBE.MC": "Iberdrola",
	"SU.PA": "Schneider Electric", "AIR.PA": "Airbus", "ENEL.MI": "Enel",
	"MUV2.DE": "Munich Re", "ITX.MC": "Inditex", "DB1.DE": "Deutsche Börse",
	"ISP.MI": "Intesa Sanpaolo", "ENI.MI": "Eni", "AI.PA": "Air Liquide",
	"INGA.AS": "ING Groep", "BAYN.DE": "Bayer", "BAS.DE": "BASF",
	"MBG.DE": "Mercedes-Benz Group", "BMW.DE": "BMW", "VOW3.DE": "Volkswagen",
	"DTE.DE": "Deutsche Telekom", "ADS.DE": "Adidas", "OR.PA": "L'Oréal",
	"BNP.PA": "BNP Paribas", "SAF.PA": "Safran", "EL.PA": "EssilorLuxottica",
	"ABI.BR": "Anheuser-Busch InBev", "ADYEN.AS": "Adyen", "RACE.MI": "Ferrari",
	"MRK.DE": "Merck", "KNEBV.HE": "KONE", "PHIA.AS": "Koninklijke Philips",
	"G.MI": "Assicurazioni Generali", "STLAM.MI": "Stellantis", "BN.PA": "Danone",
	"CA.PA": "Carrefour", "ENR.DE": "Siemens Energy", "HEIA.AS": "Heineken",
	"KER.PA": "Kering", "NN.AS": "NN Group", "PRX.AS": "Prosus",
	"RMS.PA": "Hermès International", "SAN.PA": "Sanofi", "ARGX.BR": "Argenx",
	"AKZA.AS": "AkzoNobel", "AD.AS": "Ahold Delhaize",
}


def calculate_returns(history):
	if len(history) < 2:
		return (None,) * 5
	current = history.iloc[-1]
	previous_1d = history.iloc[-2]
	previous_5d = history.iloc[-6] if len(history) >= 6 else history.iloc[0]
	last_date = history.index[-1]
	month_start = pd.Timestamp(last_date.year, last_date.month, 1)
	year_start = pd.Timestamp(last_date.year, 1, 1)
	month_data = history[history.index >= month_start]
	year_data = history[history.index >= year_start]
	previous_mtd = month_data.iloc[0] if not month_data.empty else previous_1d
	previous_ytd = year_data.iloc[0] if not year_data.empty else previous_1d
	returns = [(current / previous - 1) * 100 for previous in
				(previous_1d, previous_5d, previous_mtd, previous_ytd)]
	return (current, *returns)


def fetch_close(ticker):
	history = yf.download(ticker, period="1y", progress=False)["Close"]
	if isinstance(history, pd.DataFrame):
		history = history.iloc[:, 0]
	return history.dropna()


def performance_row(name, ticker, label):
	current, r1, r5, rmtd, rytd = calculate_returns(fetch_close(ticker))
	if r1 is None:
		return None
	return {label: name, "Ticker": ticker, "Latest Price": round(current, 2),
			"1D (%)": f"{r1:+.2f}%", "5D (%)": f"{r5:+.2f}%",
			"MTD (%)": f"{rmtd:+.2f}%", "YTD (%)": f"{rytd:+.2f}%", "_val_1d": r1}


index_rows = []
for name, ticker in indices.items():
	try:
		row = performance_row(name, ticker, "Index")
		if row:
			row.pop("Ticker")
			row.pop("Latest Price")
			row["Latest Value"] = round(calculate_returns(fetch_close(ticker))[0], 2)
			index_rows.append(row)
	except Exception as error:
		print(f"Error fetching index {name}: {error}")
df_indices = pd.DataFrame(index_rows).drop(columns=["_val_1d"], errors="ignore")

sx5e_hist = fetch_close("^STOXX50E")
sx5e_latest_val = sx5e_hist.iloc[-1]
sx5e_ytd_series = sx5e_hist[sx5e_hist.index >= pd.Timestamp(sx5e_hist.index[-1].year, 1, 1)]

stock_rows = []
for ticker, name in euro_stoxx_50_dict.items():
	try:
		row = performance_row(name, ticker, "Company")
		if row:
			stock_rows.append(row)
	except Exception as error:
		print(f"Skipping {ticker}: {error}")
df_stocks = pd.DataFrame(stock_rows)
if not df_stocks.empty:
	sorted_stocks = df_stocks.sort_values("_val_1d", ascending=False)
	top_10_gainers = sorted_stocks.head(10).drop(columns=["_val_1d"])
	top_10_losers = sorted_stocks.tail(10).sort_values("_val_1d").drop(columns=["_val_1d"])
else:
	top_10_gainers = top_10_losers = pd.DataFrame()

plt.figure(figsize=(7.0, 3.0), dpi=150)
ytd_normalized = (sx5e_ytd_series / sx5e_ytd_series.iloc[0] - 1) * 100
plt.plot(ytd_normalized.index, ytd_normalized.values, color="#003366", lw=1.5)
plt.title(f"Euro Stoxx 50 Year to Date Performance | Latest Value: {sx5e_latest_val:,.2f} ({ytd_normalized.iloc[-1]:+.2f}%)", fontsize=10, pad=10)
plt.ylabel("Return (%)", fontsize=9)
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()

img_buf = io.BytesIO()
plt.savefig(img_buf, format="png", dpi=160, bbox_inches="tight")
img_buf.seek(0)
plt.close()

html_content = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;font-size:11px">
<h2 style="color:#003366">European Equity Markets &amp; Euro Stoxx 50 Report - {today_str}</h2>
<h3>Major European Equity Indices</h3>{df_indices.to_html(index=False)}
<h3>Euro Stoxx 50 YTD Trend</h3>
<p><img src="cid:ytd_chart" alt="Euro Stoxx 50 YTD Chart" style="width:100%;max-width:650px;height:auto;display:block;"></p>
<h3>Top 10 Gainers (Euro Stoxx 50 Stocks - 1D)</h3>{top_10_gainers.to_html(index=False)}
<h3>Top 10 Losers (Euro Stoxx 50 Stocks - 1D)</h3>{top_10_losers.to_html(index=False)}
</body></html>"""

sender_email = os.environ.get("EMAIL_USER", "cpvanvliet100@gmail.com")
password = os.environ.get("EMAIL_PASS")
if not password:
	raise ValueError("EMAIL_PASS environment variable is missing!")
msg = MIMEMultipart("related")
msg["Subject"] = f"European Market & Euro Stoxx 50 Close Report - {today_str}"
msg["From"] = msg["To"] = sender_email
alternative = MIMEMultipart("alternative")
alternative.attach(MIMEText(html_content, "html"))
msg.attach(alternative)
image = MIMEImage(img_buf.read())
image.add_header("Content-ID", "<ytd_chart>")
msg.attach(image)
try:
	with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
		server.login(sender_email, password)
		server.sendmail(sender_email, sender_email, msg.as_string())
	print("Euro Stoxx 50 compact report sent successfully!")
except Exception as error:
	print(f"Error sending email: {error}")
