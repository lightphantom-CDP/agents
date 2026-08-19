"""Minimal CDE test — if this prints, Python jobs work. No arguments needed."""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cde-python-test")

logger.info("HELLO FROM CDE PYTHON argv=%s", sys.argv)
print("HELLO FROM CDE PYTHON", flush=True)

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("cde-python-test").getOrCreate()
spark.sql("SELECT 1 AS test").show()
logger.info("CDE PYTHON TEST PASSED")
print("CDE PYTHON TEST PASSED", flush=True)
