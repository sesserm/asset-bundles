import yaml, os
from delta.tables import DeltaTable
from pyspark.sql.functions import lit
from pyspark.sql.types import *

notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()

if "dev" in notebook_path:
    origen_env = "dev"
    destino_env = "pre"
elif "pre" in notebook_path:
    origen_env = "pre"
    destino_env = "prod"
else:
    print("❌ Entorno no soportado")
    dbutils.notebook.exit("")

# Ajustamos la ruta base al nivel superior donde están notebooks, tables.txt y schemas/
base_path = os.path.dirname(os.path.dirname(notebook_path))  # Sube dos niveles desde notebooks/

tables_path = os.path.join(base_path, "tables.txt")
schemas_base = os.path.join(base_path, "schemas")
dbutils.widgets.text("CATALOGO", "valor_por_defecto")
catalog = dbutils.widgets.get("CATALOGO")
print(f"CATALOGO recibido: {catalog}")

tablas_raw = [line.strip() for line in open(tables_path) if line.strip()]
tablas = [t.replace("__CATALOGO__", catalog) for t in tablas_raw]

for tabla_full in tablas:
    print(f"🔁 Migrando {tabla_full} ({origen_env} → {destino_env})")

    schema_path = os.path.join(schemas_base, f"{tabla_full}.yaml".replace(".", "_"))

    if not os.path.exists(schema_path):
        print(f"⚠️ Falta esquema para {tabla_full}")
        continue

    with open(schema_path, "r") as f:
        schema_config = yaml.safe_load(f)

    fields = []
    for col in schema_config["columns"]:
        col_type = col["type"].lower()
        dtype = {
            "string": StringType(),
            "boolean": BooleanType(),
            "double": DoubleType(),
            "integer": IntegerType(),
            "long": LongType()
        }.get(col_type)

        if dtype is None:
            raise Exception(f"❌ Tipo no soportado: {col_type}")
        fields.append(StructField(col["name"], dtype, col["nullable"]))

    schema = StructType(fields)

    try:
        spark.read.table(tabla_full)
        print("✅ Tabla ya existe")
    except:
        print("📐 Creando tabla")
        spark.createDataFrame([], schema).write.format("delta").saveAsTable(tabla_full)

    try:
        df_origen = spark.read.table(tabla_full).filter(f"env = '{origen_env}'")
        if df_origen.rdd.isEmpty():
            print("ℹ️ Nada para migrar")
            continue

        df_destino = df_origen.drop("env").withColumn("env", lit(destino_env))

        delta_table = DeltaTable.forName(spark, tabla_full)
        delta_table.alias("t") \
            .merge(df_destino.alias("s"), "t.id = s.id AND t.env = s.env") \
            .whenMatchedUpdateAll() \
            .whenNotMatchedInsertAll() \
            .execute()
        print("✅ Migración exitosa")
    except Exception as e:
        print(f"❌ Error: {e}")
