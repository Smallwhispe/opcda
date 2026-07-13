import logging
import time
from typing import Optional

import OpenOPC

from services.predict_result import get_recent_n


OPC_SERVER_NAME = "Company.FactorySoftOpcDaSim"
TAGS = ["pressure", "c5", "bing_xi", "gan_dian"]
WRITE_INTERVAL = 10
ERROR_RETRY_DELAY = 5
SLEEP_GRANULARITY = 0.1

logger = logging.getLogger("OPC_DA_Service")


class OpcDaService:
    def __init__(self):
        self.server_name = OPC_SERVER_NAME
        self._running = False

    def stop(self):
        logger.info("[OPC-DA写] 正在停止服务...")
        self._running = False

    def run(self):
        logger.info("--- [启动] OPC DA 写入服务 ---")
        logger.info("  服务端: %s", self.server_name)
        logger.info("  点位:   %s", TAGS)
        logger.info("  间隔:   %ss", WRITE_INTERVAL)
        self._running = True

        while self._running:
            opc = None
            try:
                opc = OpenOPC.client()
                opc.connect(self.server_name, "localhost")

                records = get_recent_n(1)
                if not records:
                    logger.warning("[OPC-DA写] 数据库无数据，等待中...")
                    self._sleep_until_next_cycle(ERROR_RETRY_DELAY)
                    continue

                record = records[0]
                current_ts = record.get("ts")
                write_group = self._build_write_group(record)

                if not write_group:
                    logger.warning("[OPC-DA写] 无有效数据可写入")
                    self._sleep_until_next_cycle(WRITE_INTERVAL)
                    continue

                results = opc.write(write_group, include_error=False)
                status_msgs = self._format_write_results(results, write_group)
                logger.info(
                    "[OPC-DA写] TS:%s | %s",
                    current_ts,
                    ", ".join(status_msgs),
                )
                self._sleep_until_next_cycle(WRITE_INTERVAL)

            except Exception as e:
                logger.error("[OPC-DA写] 循环异常: %s", e, exc_info=True)
                self._sleep_until_next_cycle(ERROR_RETRY_DELAY)
            finally:
                if opc is not None:
                    try:
                        opc.close()
                    except Exception:
                        pass

        logger.info("[OPC-DA写] 服务已停止")

    def _build_write_group(self, record):
        write_group = []
        for tag_name in TAGS:
            value = self._safe_float(record.get(tag_name))
            if value is None:
                continue
            write_group.append((tag_name, value))
        return write_group

    def _format_write_results(self, results, write_group):
        if isinstance(results, tuple):
            results = [results]

        status_by_tag = {}
        if isinstance(results, list):
            for index, item in enumerate(results):
                if isinstance(item, tuple):
                    if len(item) >= 2 and item[0] in TAGS:
                        status_by_tag[item[0]] = item[1]
                    elif len(item) >= 1 and index < len(write_group):
                        status_by_tag[write_group[index][0]] = item[0]
                elif index < len(write_group):
                    status_by_tag[write_group[index][0]] = str(item)

        status_msgs = []
        for tag_name, value in write_group:
            status = status_by_tag.get(tag_name, "Unknown")
            if status == "Success":
                status_msgs.append(f"{tag_name}={value:.4f}=OK")
            else:
                status_msgs.append(f"{tag_name}={value:.4f}=FAIL({status})")
        return status_msgs

    def _sleep_until_next_cycle(self, seconds):
        loops = max(1, int(seconds / SLEEP_GRANULARITY))
        for _ in range(loops):
            if not self._running:
                return
            time.sleep(SLEEP_GRANULARITY)

    def _safe_float(self, value) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
