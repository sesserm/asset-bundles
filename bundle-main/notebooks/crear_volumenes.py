import os

volumes_path = "/Workspace/tmp/volumes.txt"
catalog = os.environ.get("CATALOGO", "")
if not os.path.exists(volumes_path):
    print("ℹ️ No hay archivo de volúmenes definido.")
    dbutils.notebook.exit("")

volumenes_raw = [line.strip() for line in open(volumes_path) if line.strip() and not line.startswith("#")]
volumenes = [v.replace("__CATALOGO__", catalog) for v in volumenes_raw]

if not volumenes:
    print("ℹ️ No hay volúmenes a crear.")
else:
    for vol in volumenes:
        try:
            parts = vol.split(".")
            if len(parts) != 3:
                print(f"❌ Formato inválido: {vol}")
                continue

            catalog, schema, volumen = parts
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
            spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.{volumen}")
            print(f"✅ Volumen creado: {vol}")
        except Exception as e:
            print(f"❌ Error al crear volumen {vol}: {e}")
