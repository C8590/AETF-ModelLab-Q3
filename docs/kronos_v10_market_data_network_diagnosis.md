# Kronos V0.10.2-C Market Data Network Diagnosis

- 运行时间: 2026-06-03T23:11:29
- Python 路径: E:\AETF-ModelLab\.venv\Scripts\python.exe
- AkShare 最小测试: FAIL (rows=0)
- BaoStock 最小测试: FAIL (symbol=, rows=0)
- Windows winhttp proxy 状态: PASS

## Proxy Environment

- HTTP_PROXY: missing
- HTTPS_PROXY: missing
- ALL_PROXY: missing
- NO_PROXY: missing

## winhttp proxy

```text
Current WinHTTP proxy settings:

    Proxy Server(s) :  http=127.0.0.1:10809;https=127.0.0.1:10809
    Bypass List     :  localhost;127.*;^<local^>
```

## Errors

- AkShare: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20240101&end=20240201&secid=1.510300 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))
- BaoStock: BaoStock returned zero rows.

## Scope

- 未训练模型。
- 未运行 torchrun。
- 未调用 GPU 推理。
- 未接入或回写主项目。
- 未生成交易建议。
