"""Minimal CDE test — if this prints, Python jobs work. No arguments needed."""

import sys

print("HELLO FROM CDE PYTHON", flush=True)
sys.stdout.flush()
sys.stderr.write("HELLO STDERR\n")
sys.stderr.flush()

from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("cde-python-test").getOrCreate()
print("SPARK SESSION OK", flush=True)
spark.sql("SELECT 1 AS test").show()
print("CDE PYTHON TEST PASSED", flush=True)
