# Kronos V0.10.2-A AkShare ETF Kline Download Report

- 运行时间: 2026-06-03T21:23:39
- 数据源: akshare.fund_etf_hist_em
- 下载区间: 20180101 至 20260603
- 周期: daily
- 复权: qfq
- ETF 配置数量: 20
- 成功数量: 15
- 失败数量: 5
- raw kline 输出目录: E:/AETF-ModelLab/data/real/raw/kline
- manifest 路径: E:/AETF-ModelLab/outputs/real_data/kronos_v10_akshare_download_manifest.json

## 每只 ETF 下载结果

| symbol | display_name | market | status | acquisition | bar_count | start_date | end_date | raw_path | failure_reason |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| 510300 | 沪深300ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/510300.csv | - |
| 510500 | 中证500ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/510500.csv | - |
| 510050 | 上证50ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/510050.csv | - |
| 159915 | 创业板ETF | SZ | PASS | existing_standardized_raw_csv | 2039 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/159915.csv | - |
| 159949 | 创业板50ETF | SZ | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/159949.csv | - |
| 512100 | 中证1000ETF | SH | PASS | existing_standardized_raw_csv | 2039 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512100.csv | - |
| 588000 | 科创50ETF | SH | PASS | existing_standardized_raw_csv | 1344 | 2020-11-16 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/588000.csv | - |
| 588080 | 科创板50ETF | SH | PASS | existing_standardized_raw_csv | 1344 | 2020-11-16 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/588080.csv | - |
| 512880 | 证券ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512880.csv | - |
| 512800 | 银行ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512800.csv | - |
| 512660 | 军工ETF | SH | PASS | existing_standardized_raw_csv | 2040 | 2018-01-02 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512660.csv | - |
| 512690 | 酒ETF | SH | PASS | existing_standardized_raw_csv | 1717 | 2019-05-06 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512690.csv | - |
| 515030 | 新能源车ETF | SH | PASS | existing_standardized_raw_csv | 1515 | 2020-03-04 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/515030.csv | - |
| 512760 | 芯片ETF | SH | PASS | existing_standardized_raw_csv | 1691 | 2019-06-12 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512760.csv | - |
| 512480 | 半导体ETF | SH | PASS | existing_standardized_raw_csv | 1691 | 2019-06-12 | 2026-06-03 | E:/AETF-ModelLab/data/real/raw/kline/512480.csv | - |
| 159928 | 消费ETF | SZ | FAIL |  | 0 |  |  |  | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159928 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| 159996 | 家电ETF | SZ | FAIL |  | 0 |  |  |  | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159996 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| 159992 | 创新药ETF | SZ | FAIL |  | 0 |  |  |  | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159992 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| 512010 | 医药ETF | SH | FAIL |  | 0 |  |  |  | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=1.512010 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |
| 159937 | 黄金ETF | SZ | FAIL |  | 0 |  |  |  | HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159937 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response'))) |

## Scope

- 本阶段只下载并标准化真实 A 股 ETF 日线 K 线。
- 未处理或伪造 left_candidates_history.csv。
- 未训练模型。
- 未运行 torchrun。
- 未调用 GPU 推理。
- 未接入或回写主项目。
- 未生成交易建议。

## 失败原因

- 159928: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159928 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))
- 159996: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159996 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))
- 159992: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159992 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))
- 512010: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=1.512010 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))
- 159937: HTTPSConnectionPool(host='push2his.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/kline/get?fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61%2Cf116&ut=7eea3edcaed734bea9cbfc24409ed989&klt=101&fqt=1&beg=20180101&end=20260603&secid=0.159937 (Caused by ProxyError('Unable to connect to proxy', RemoteDisconnected('Remote end closed connection without response')))

## 下载概览

- 成功 ETF 最小 bar_count: 1344
