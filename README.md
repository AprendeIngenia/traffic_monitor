# 🚦 Sistema de Monitoreo de Tráfico con Visión Artificial

***Banner por añadir***

Un sistema de escritorio avanzado y robusto, desarrollado en **Python** y **PySide6**, para el análisis de video en tiempo real. Permite el conteo, seguimiento y estimación de velocidad de vehículos, utilizando técnicas de vanguardia en visión por computadora e inteligencia artificial.

---

## ✨ Características Principales

* **Detección y Seguimiento de Vehículos:** Utiliza el potente modelo **YOLO** para la detección y asignación de un ID único a cada vehículo.
* **Conteo por Carril:** Realiza un conteo preciso de los vehículos que cruzan líneas de conteo virtuales, diferenciado por cada carril.
* **Estimación de Velocidad Precisa:** Implementa un **Filtro de Kalman** sobre una transformación de **Homografía** para calcular la velocidad de los vehículos en km/h de manera estable y confiable.
* **Interfaz Gráfica Interactiva:** Una UI moderna y responsiva construida con PySide6 que permite:
    * Configuración visual de carriles mediante polígonos interactivos.
    * Calibración de la perspectiva de la cámara con un asistente de 4 puntos.
    * Carga de videos pre-grabados o uso de cámaras en tiempo real.
* **Dashboard de Métricas en Tiempo Real:** Visualiza estadísticas agregadas por carril y globales (velocidad promedio/mín/máx, conteo por tipo, distribución de velocidad).
* **Exportación de Datos:** Genera reportes detallados en formato `.csv` con todos los eventos registrados para un análisis posterior.
* **Arquitectura Multi-hilo:** Garantiza que la interfaz nunca se congele, sin importar la carga de trabajo del procesamiento de video.

---

## 🚀 Demostración en Vivo

***(GIF mostrando la configuración de carriles, el análisis en tiempo real y el dashboard de métricas)***

---

## 🏗️ Arquitectura del Sistema

El sistema se fundamenta en una **arquitectura desacoplada de tres capas**, optimizada para aplicaciones de visión artificial que requieren un alto rendimiento y una interfaz de usuario fluida.

***Diagrama del sistema***

### 1. Capa de Frontend

-   **Tecnología:** PySide6 (Qt para Python).
-   **Responsabilidad:** Es el centro de mando del usuario. Su única función es presentar datos y capturar interacciones. No contiene lógica de negocio.
-   **Componentes Clave:**
    -   `MainWindow`: Orquesta las pestañas y la comunicación.
    -   Pestañas Modulares (`VideoAnalysisTab`, `LaneConfigurationTab`, `HomographyConfigurationTab`, `MetricsTab`): Cada una encapsula una funcionalidad específica.
    -   `ClickableLabel` y `QPainter`: Componentes personalizados que permiten una configuración visual e interactiva de las zonas de interés, proporcionando retroalimentación inmediata al usuario.

### 2. Capa de Backend

-   **Tecnología:** OpenCV, PyTorch, NumPy, Shapely.
-   **Responsabilidad:** Es el cerebro del sistema. Ejecuta todo el pipeline de procesamiento de visión artificial en un **hilo de trabajo (`QThread`) separado** para no bloquear la interfaz.
-   **Pipeline por Fotograma:**
    1.  **Medición de Tiempo (`delta_t`):** Calcula el tiempo real transcurrido para una estimación de velocidad precisa.
    2.  **Enmascaramiento de ROI:** Aísla las zonas de los carriles para optimizar la detección.
    3.  **Detección y Seguimiento (YOLO):** Infiere y asigna un ID único a cada vehículo.
    4.  **Cálculo de Homografía:** Transforma las coordenadas de la imagen a un plano del mundo real.
    5.  **Estimación de Velocidad (Filtro de Kalman):** Suaviza las mediciones y proporciona velocidades estables.
    6.  **Lógica de Conteo:** Registra los cruces de línea y agrega las estadísticas.

### 3. Capa de Comunicación

-   **Tecnología:** Señales y Slots de Qt.
-   **Responsabilidad:** Actúa como el sistema nervioso del software, conectando el Frontend y el Backend de manera asíncrona y segura entre hilos.
    -   **Flujo de Configuración:** Las acciones en la UI (ej. cargar un video) emiten señales que el backend recibe.
    -   **Flujo de Resultados:** El `VideoProcessor` (backend) emite una señal `analysisResult(dict)` con el paquete completo de estadísticas en cada fotograma. `MainWindow` la recibe y la distribuye a los slots correspondientes en las pestañas `VideoAnalysisTab` y `MetricsTab` para actualizar la visualización.

---

## 🔬 Inmersión Técnica Profunda (Technical Deep Dive)

### Homografía y Corrección de Perspectiva

Para medir distancias y velocidades reales, es crucial corregir la distorsión de la perspectiva de la cámara.

-   **Concepto:** Utilizamos una transformación de **Homografía**, una matriz $H$ de 3x3 que mapea puntos de un plano (la imagen) a otro (el suelo).
-   **Implementación:** Se implementa un método de **calibración de 4 puntos**. El usuario define un rectángulo en la imagen (por ejemplo, un área que abarca un carril) y proporciona sus dimensiones reales (ancho y largo en metros). La función `cv2.findHomography` calcula la matriz $H$ que realiza esta transformación. Cualquier punto $(u,v)$ en la imagen puede ser transformado a su coordenada real $(X,Y)$ mediante esta matriz.

> $$ s \begin{bmatrix} X \\ Y \\ 1 \end{bmatrix} = \mathbf{H} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} $$

### Estimación de Velocidad con Filtro de Kalman

Las coordenadas de los cuadros delimitadores de YOLO presentan un "ruido" o *jitter* natural. Calcular la velocidad directamente a partir de la diferencia de posición entre dos fotogramas produce resultados extremadamente volátiles.

-   **Concepto:** Para solucionar esto, implementamos un **Filtro de Kalman** para cada vehículo rastreado (`track_id`). Este es un estimador recursivo que modela el estado de un sistema dinámico y lo corrige con mediciones ruidosas.
-   **Implementación:**
    1.  **Estado del Vehículo:** Se define como $\vec{x} = [x, y, v_x, v_y]^T$, donde $(x,y)$ es la posición en el mundo real y $(v_x, v_y)$ es su velocidad.
    2.  **Ciclo Predecir-Actualizar:**
        -   **Predecir:** El filtro predice la nueva posición y velocidad del vehículo basándose en su estado anterior y un modelo de movimiento.
        -   **Actualizar:** La posición detectada por YOLO se transforma a coordenadas del mundo real (usando la homografía) y se usa como la "medición" para corregir la predicción del filtro.
    3.  **Resultado:** El filtro produce una trayectoria suavizada y una estimación de velocidad estable y físicamente coherente, inmune al *jitter* de la detección.

***Diagrama flujo de datos***

---

## 📂 Estructura del Proyecto


traffic_monitor/
│
├── resources/                # Archivos estáticos como iconos y modelos pre-entrenados
│   └── detection_models/
│       └── yolo11s.pt
│
├── src/
│   ├── core/                 # Lógica de backend (procesamiento de visión)
│   │   ├── counting_processor.py
│   │   ├── homography_manager.py
│   │   ├── mask_processor.py
│   │   ├── speed_calculator.py
│   │   ├── vehicle_detector.py
│   │   └── video_processor.py  # El orquestador del hilo de trabajo
│   │
│   ├── ui/                   # Componentes de la interfaz de usuario (Frontend)
│   │   ├── homography_configuration_tab.py
│   │   ├── lane_configuration_tab.py
│   │   ├── main_window.py
│   │   ├── metrics_tab.py
│   │   └── video_analysis_tab.py
│   │
│   └── main.py               # Punto de entrada de la aplicación
│
└── requirements.txt          # Dependencias del proyecto


---

## ⚙️ Instalación y Uso

### Prerrequisitos

-   Python 3.10 o superior
-   Git
-   (Opcional pero recomendado) Una GPU NVIDIA compatible con CUDA para un rendimiento óptimo.

### Guía de Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/tu-usuario/traffic_monitor.git](https://github.com/tu-usuario/traffic_monitor.git)
    cd traffic_monitor
    ```

2.  **Crear y activar un entorno virtual:**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instalar las dependencias:**
    *El archivo `requirements.txt` debería crearse con las versiones correctas.*
    ```bash
    pip install -r requirements.txt
    ```
    *Nota: La instalación de PyTorch puede variar. Consulta su [sitio web oficial](https://pytorch.org/get-started/locally/) para obtener el comando correcto para tu sistema (CPU o versión específica de CUDA).*

4.  **Ejecutar la aplicación:**
    ```bash
    python src/main.py
    ```

### Guía de Uso Rápido

1.  **Cargar Video:** Inicia la aplicación y haz clic en "📂 Cargar Video" o "📷 Usar Cámara". El primer fotograma aparecerá en las vistas previas.
2.  **Configurar Homografía:** Ve a la pestaña "Corrección Homográfica". Define un rectángulo en el suelo de la imagen cuyos puntos conozcas (ej. P1 a P4) y anota sus dimensiones reales en metros.
3.  **Configurar Carriles:** Ve a la pestaña "Configuración de Carriles". Ajusta el número de carriles y define los 4 puntos que delimitan cada área de interés.
4.  **Iniciar Análisis:** Vuelve a la pestaña "Análisis de Video". El botón "▶️ Iniciar Análisis" ya debería estar activo. ¡Púlsalo para empezar!
5.  **Revisar y Exportar:** Explora las métricas en tiempo real en la pestaña "Métricas" y exporta el reporte completo cuando lo necesites.

---

## 🛣️ Futuras Mejoras (Roadmap)

-   [ ] Implementar guardado y carga de la configuración del proyecto (puntos de carril y homografía).
-   [ ] Soporte para diferentes ángulos de cámara (ej. vistas laterales).
-   [ ] Integración con una base de datos para el almacenamiento persistente de estadísticas.
-   [ ] Creación de un dashboard web para la visualización remota de los resultados.
-   [ ] Añadir clasificación más detallada (ej. diferenciar entre furgoneta y camión).

---

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.