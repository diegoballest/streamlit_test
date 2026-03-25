import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(page_title="Carga de CSV", layout="wide")

st.title("📂 Cargar archivo CSV")

# Subir archivo
archivo = st.file_uploader("Sube tu archivo CSV", type=["csv"])

if archivo is not None:
    try:
        # Leer CSV
        df = pd.read_csv(archivo)
        st.success("Archivo cargado correctamente ✅")

        # Copia de trabajo
        df_filtrado = df.copy()

        # =========================
        # 📅 FILTRO POR FECHAS
        # =========================
        st.subheader("📅 Filtro por fechas")

        usar_filtro_fecha = st.checkbox("Activar filtro por rango de fechas")

        if usar_filtro_fecha:
            fecha_col = st.selectbox(
                "Selecciona la columna de fecha",
                df.columns,
                key="fecha_col"
            )

            try:
                df_filtrado[fecha_col] = pd.to_datetime(
                    df_filtrado[fecha_col],
                    errors="coerce"
                )
                df_filtrado = df_filtrado.dropna(subset=[fecha_col])

                if df_filtrado.empty:
                    st.warning("No se pudieron convertir fechas válidas en esa columna.")
                else:
                    fecha_min = df_filtrado[fecha_col].min().date()
                    fecha_max = df_filtrado[fecha_col].max().date()

                    rango_fechas = st.date_input(
                        "Selecciona el rango de fechas",
                        value=(fecha_min, fecha_max),
                        min_value=fecha_min,
                        max_value=fecha_max,
                        key="rango_fechas"
                    )

                    if len(rango_fechas) == 2:
                        fecha_inicio, fecha_fin = rango_fechas

                        df_filtrado = df_filtrado[
                            (df_filtrado[fecha_col].dt.date >= fecha_inicio) &
                            (df_filtrado[fecha_col].dt.date <= fecha_fin)
                        ]

            except Exception as e:
                st.error(f"Error al filtrar fechas: {e}")

        # =========================
        # 📞 FILTRO POR TELÉFONO
        # =========================
        st.subheader("📞 Filtro por número telefónico")

        usar_filtro_telefono = st.checkbox("Activar filtro por número telefónico")

        if usar_filtro_telefono:
            tel_col1, tel_col2 = st.columns(2)

            telefono_origen_col = tel_col1.selectbox(
                "Columna de número origen",
                df_filtrado.columns,
                key="telefono_origen_col"
            )

            telefono_destino_col = tel_col2.selectbox(
                "Columna de número destino",
                df_filtrado.columns,
                key="telefono_destino_col"
            )

            opcion_filtro_tel = st.radio(
                "Modo de filtro",
                ["Buscar por texto", "Seleccionar números"],
                horizontal=True,
                key="modo_tel"
            )

            if opcion_filtro_tel == "Buscar por texto":
                texto_tel = st.text_input(
                    "Escribe el número o parte del número",
                    key="texto_tel"
                )

                if texto_tel:
                    mask_origen = (
                        df_filtrado[telefono_origen_col]
                        .astype(str)
                        .str.contains(texto_tel, case=False, na=False)
                    )

                    mask_destino = (
                        df_filtrado[telefono_destino_col]
                        .astype(str)
                        .str.contains(texto_tel, case=False, na=False)
                    )

                    df_filtrado = df_filtrado[mask_origen | mask_destino]

            else:
                numeros_origen = (
                    df_filtrado[telefono_origen_col]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                numeros_destino = (
                    df_filtrado[telefono_destino_col]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                valores_telefono = sorted(list(set(numeros_origen + numeros_destino)))

                telefonos_seleccionados = st.multiselect(
                    "Selecciona uno o varios números",
                    options=valores_telefono,
                    key="telefonos_sel"
                )

                if telefonos_seleccionados:
                    mask_origen = df_filtrado[telefono_origen_col].astype(str).isin(telefonos_seleccionados)
                    mask_destino = df_filtrado[telefono_destino_col].astype(str).isin(telefonos_seleccionados)

                    df_filtrado = df_filtrado[mask_origen | mask_destino]

        # =========================
        # 📊 RESUMEN DEL DATASET FILTRADO
        # =========================
        st.subheader("📊 Resumen de información del dataset")

        col1, col2, col3 = st.columns(3)
        col1.metric("Filas filtradas", df_filtrado.shape[0])
        col2.metric("Columnas", df_filtrado.shape[1])
        col3.metric(
            "Columnas numéricas",
            len(df_filtrado.select_dtypes(include="number").columns)
        )

        st.subheader("👀 Vista previa")
        st.dataframe(df_filtrado, use_container_width=True)

        # =========================
        # 🗺️ MAPA + HEATMAP
        # =========================
        st.subheader("🗺️ Mapa de datos")
        st.markdown("### Selecciona columnas de coordenadas")

        map_col1, map_col2 = st.columns(2)

        lat_col = map_col1.selectbox(
            "Columna de Latitud",
            df_filtrado.columns,
            key="lat_col"
        )
        lon_col = map_col2.selectbox(
            "Columna de Longitud",
            df_filtrado.columns,
            key="lon_col"
        )

        try:
            df_map = df_filtrado.copy()
            df_map[lat_col] = pd.to_numeric(df_map[lat_col], errors="coerce")
            df_map[lon_col] = pd.to_numeric(df_map[lon_col], errors="coerce")
            df_map = df_map.dropna(subset=[lat_col, lon_col])

            if df_map.empty:
                st.warning("No hay coordenadas válidas para mostrar en el mapa.")
            else:
                st.markdown("### Opciones del mapa")
                usar_heatmap = st.checkbox("Mostrar Heatmap", value=True, key="usar_heatmap")
                agrupar = st.checkbox("Agrupar puntos cercanos", value=True, key="agrupar")

                centro = [df_map[lat_col].mean(), df_map[lon_col].mean()]
                mapa = folium.Map(location=centro, zoom_start=12)

                if usar_heatmap:
                    if agrupar:
                        df_map["lat_r"] = df_map[lat_col].round(4)
                        df_map["lon_r"] = df_map[lon_col].round(4)

                        agrupado = (
                            df_map.groupby(["lat_r", "lon_r"])
                            .size()
                            .reset_index(name="conteo")
                        )

                        heat_data = agrupado[["lat_r", "lon_r", "conteo"]].values.tolist()
                    else:
                        heat_data = df_map[[lat_col, lon_col]].values.tolist()

                    HeatMap(
                        heat_data,
                        radius=20,
                        blur=15
                    ).add_to(mapa)

                else:
                    for _, row in df_map.iterrows():
                        folium.CircleMarker(
                            location=[row[lat_col], row[lon_col]],
                            radius=4,
                            fill=True
                        ).add_to(mapa)

                st_folium(mapa, width=1200, height=600)

        except Exception as e:
            st.error(f"Error en el mapa: {e}")

        # =========================
        # 🔎 EXPLORAR COLUMNAS
        # =========================
        st.subheader("🔎 Explorar columnas")

        columna = st.selectbox(
            "Selecciona una columna",
            df_filtrado.columns,
            key="explorar_columna"
        )

        st.write(f"Valores más frecuentes en '{columna}':")
        st.write(df_filtrado[columna].value_counts(dropna=False).head(10))

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

else:
    st.info("Sube un archivo CSV para comenzar")
