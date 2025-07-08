import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
import argparse
import os

class HomographyDemo:
    def __init__(self, image_path, image_points, real_width_m, real_length_m):
        """
        Clase para demostrar la corrección de homografía y cálculo de velocidad
        
        Args:
            image_path (str): Ruta de la imagen de la carretera
            image_points (list): 4 puntos de referencia [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
            real_width_m (float): Ancho real en metros
            real_length_m (float): Largo real en metros
        """
        self.image_path = image_path
        self.image_points = np.float32(image_points)
        self.real_width_m = real_width_m
        self.real_length_m = real_length_m
        
        # Cargar imagen
        self.original_image = cv2.imread(image_path)
        if self.original_image is None:
            raise ValueError(f"No se pudo cargar la imagen: {image_path}")
        
        self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
        self.height, self.width = self.original_image.shape[:2]
        
        # Calcular matriz de homografía
        self.homography_matrix = self._calculate_homography()
        
        # Crear imagen corregida
        self.corrected_image = self._create_corrected_image()
        
    def _calculate_homography(self):
        """Calcula la matriz de homografía"""
        # Puntos destino en el mundo real (rectángulo perfecto)
        dst_points = np.float32([
            [0, self.real_length_m],         # Arriba-Izquierda
            [self.real_width_m, self.real_length_m],   # Arriba-Derecha  
            [self.real_width_m, 0],          # Abajo-Derecha
            [0, 0]                           # Abajo-Izquierda
        ])
        
        # Calcular matriz de homografía
        matrix, _ = cv2.findHomography(self.image_points, dst_points)
        return matrix
    
    def _create_corrected_image(self):
        """
        Crea la imagen con perspectiva corregida usando una matriz específica para la visualización.
        """
        # 1. Definir una escala para la imagen de salida (ej: cuántos píxeles por metro)
        PIXELS_PER_METER = 100 
        
        # 2. Calcular las dimensiones de la imagen de salida en píxeles
        corrected_width_px = int(self.real_width_m * PIXELS_PER_METER)
        corrected_height_px = int(self.real_length_m * PIXELS_PER_METER)

        # 3. Puntos de destino para la VISUALIZACIÓN (un rectángulo perfecto en píxeles)
        dst_points_visual = np.float32([
            [0, corrected_height_px],
            [corrected_width_px, corrected_height_px],
            [corrected_width_px, 0],
            [0, 0]
        ])

        # 4. Calcular matriz de homografía
        visual_homography_matrix, _ = cv2.findHomography(self.image_points, dst_points_visual)

        # 5. Aplicar la transformación de perspectiva usando la matriz VISUAL
        corrected = cv2.warpPerspective(
            self.original_image, 
            visual_homography_matrix, 
            (corrected_width_px, corrected_height_px)
        )
        
        return corrected
    
    def transform_point(self, image_point):
        """Transforma un punto de imagen a coordenadas reales"""
        point = np.array([image_point], dtype=np.float32).reshape(-1, 1, 2)
        real_point = cv2.perspectiveTransform(point, self.homography_matrix)
        return tuple(real_point[0][0])
    
    def demo_1_perspective_problem(self):
        """Demuestra el problema de perspectiva"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Imagen original con distorsión
        ax1.imshow(self.original_image)
        ax1.set_title("❌ PROBLEMA: Vista con Distorsión de Perspectiva", 
                     fontsize=14, fontweight='bold', color='red')
        
        # Dibujar los puntos de referencia
        polygon = patches.Polygon(self.image_points, linewidth=3, 
                                edgecolor='yellow', facecolor='yellow', alpha=0.3)
        ax1.add_patch(polygon)
        
        # Marcar puntos individualmente
        for i, point in enumerate(self.image_points):
            ax1.plot(point[0], point[1], 'ro', markersize=8)
            ax1.annotate(f'P{i+1}', (point[0], point[1]), 
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=10, fontweight='bold', color='white',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7))
        
        # Agregar líneas para mostrar distorsión
        ax1.plot([self.image_points[0][0], self.image_points[1][0]], 
                [self.image_points[0][1], self.image_points[1][1]], 
                'r--', linewidth=2, label=f'{self.real_length_m}m (distorsionado)')
        ax1.plot([self.image_points[1][0], self.image_points[2][0]], 
                [self.image_points[1][1], self.image_points[2][1]], 
                'b--', linewidth=2, label=f'{self.real_width_m}m (distorsionado)')
        
        ax1.legend()
        ax1.set_xlim(0, self.width)
        ax1.set_ylim(self.height, 0)
        ax1.grid(True, alpha=0.3)
        
        # Vista aérea ideal
        ax2.set_xlim(0, self.real_width_m)
        ax2.set_ylim(0, self.real_length_m)
        ax2.set_aspect('equal')
        ax2.set_title("✅ OBJETIVO: Vista Aérea Perfecta", 
                     fontsize=14, fontweight='bold', color='green')
        
        # Dibujar rectángulo perfecto
        rect = Rectangle((0, 0), self.real_width_m, self.real_length_m, 
                        linewidth=3, edgecolor='green', facecolor='lightgreen', alpha=0.3)
        ax2.add_patch(rect)
        
        # Etiquetas de medidas
        ax2.annotate(f'{self.real_width_m}m', 
                    (self.real_width_m/2, -0.1), ha='center', va='top',
                    fontsize=12, fontweight='bold')
        ax2.annotate(f'{self.real_length_m}m', 
                    (-0.1, self.real_length_m/2), ha='right', va='center',
                    fontsize=12, fontweight='bold', rotation=90)
        
        ax2.grid(True, alpha=0.5)
        ax2.set_xlabel('Ancho (metros)', fontsize=12)
        ax2.set_ylabel('Largo (metros)', fontsize=12)
        
        plt.tight_layout()
        plt.savefig('examples/images/demo_1_problema_perspectiva.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("🔍 ANÁLISIS DEL PROBLEMA:")
        print(f"   • En la imagen, el rectángulo se ve distorsionado")
        print(f"   • Las líneas paralelas no son paralelas en la imagen")
        print(f"   • Un metro cerca vs un metro lejos tienen tamaños diferentes")
        print(f"   • Esto hace imposible medir velocidades reales\n")
    
    def demo_2_homography_correction(self):
        """Demuestra la corrección de homografía"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Imagen original
        ax1.imshow(self.original_image) 
        ax1.set_title("ANTES: Imagen Original", fontsize=14, fontweight='bold')
        
        # Dibujar puntos de referencia
        polygon = patches.Polygon(self.image_points, linewidth=2, 
                                edgecolor='red', facecolor='red', alpha=0.2)
        ax1.add_patch(polygon)
        
        for i, point in enumerate(self.image_points):
            ax1.plot(point[0], point[1], 'ro', markersize=6)
            ax1.annotate(f'P{i+1}', (point[0], point[1]), 
                        xytext=(5, 5), textcoords='offset points')
        
        ax1.set_xlim(0, self.width)
        ax1.set_ylim(self.height, 0)
        
        # Imagen corregida
        ax2.imshow(self.corrected_image)
        ax2.set_title("DESPUÉS: Perspectiva Corregida", fontsize=14, fontweight='bold', color='green')
        
        # Añadir grid para mostrar medidas reales
        corrected_h, corrected_w = self.corrected_image.shape[:2]
        
        # Líneas de referencia cada metro
        for i in range(1, int(self.real_width_m)):
            x_pos = (i / self.real_width_m) * corrected_w
            ax2.axvline(x=x_pos, color='white', linestyle='--', alpha=0.7)
            ax2.text(x_pos, 10, f'{i}m', color='white', fontweight='bold')
            
        for i in range(1, int(self.real_length_m)):
            y_pos = (i / self.real_length_m) * corrected_h
            ax2.axhline(y=y_pos, color='white', linestyle='--', alpha=0.7)
            ax2.text(5, y_pos, f'{i}m', color='white', fontweight='bold')
        
        ax2.set_xlim(0, corrected_w)
        ax2.set_ylim(corrected_h, 0)
        
        plt.tight_layout()
        plt.savefig('examples/images/demo_2_correccion_homografia.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("🔧 PROCESO DE CORRECCIÓN:")
        print(f"   • Matriz de homografía calculada: 3x3")
        print(f"   • Transformación aplicada: {self.width}x{self.height} → {self.corrected_image.shape[1]}x{self.corrected_image.shape[0]}")
        print(f"   • Cada píxel ahora representa una distancia real constante")
        print(f"   • Escalas: {self.corrected_image.shape[1]/self.real_width_m:.1f} px/m horizontal, {self.corrected_image.shape[0]/self.real_length_m:.1f} px/m vertical\n")
    
    def demo_3_speed_calculation(self):
        """Demuestra el cálculo de velocidad"""
        # Simular trayectoria de un vehículo
        # Trayectoria en imagen original (simulada)
        trajectory_image = [
            (600, 800),  # Posición inicial
            (650, 750),  # Posición intermedia
            (700, 700),  # Posición final
        ]
        
        # Transformar trayectoria a coordenadas reales
        trajectory_real = [self.transform_point(point) for point in trajectory_image]
        
        # Simular tiempos (30 FPS = 0.033s por frame)
        time_intervals = [0.0, 0.033, 0.066]  # segundos
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. Trayectoria en imagen original
        ax1.imshow(self.original_image)
        ax1.set_title("1. Trayectoria en Imagen Original", fontsize=12, fontweight='bold')
        
        # Dibujar trayectoria
        x_coords = [p[0] for p in trajectory_image]
        y_coords = [p[1] for p in trajectory_image]
        ax1.plot(x_coords, y_coords, 'r-', linewidth=3, label='Trayectoria')
        ax1.scatter(x_coords, y_coords, c='red', s=100, zorder=5)
        
        for i, (x, y) in enumerate(trajectory_image):
            ax1.annotate(f't{i}', (x, y), xytext=(5, 5), textcoords='offset points',
                        fontsize=10, fontweight='bold', color='white',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='red'))
        
        ax1.legend()
        ax1.set_xlim(0, self.width)
        ax1.set_ylim(self.height, 0)
        
        # 2. Trayectoria transformada
        ax2.set_xlim(0, self.real_width_m)
        ax2.set_ylim(0, self.real_length_m)
        ax2.set_aspect('equal')
        ax2.set_title("2. Trayectoria en Coordenadas Reales", fontsize=12, fontweight='bold')
        
        # Dibujar trayectoria real
        x_real = [p[0] for p in trajectory_real]
        y_real = [p[1] for p in trajectory_real]
        ax2.plot(x_real, y_real, 'g-', linewidth=3, label='Trayectoria Real')
        ax2.scatter(x_real, y_real, c='green', s=100, zorder=5)
        
        for i, (x, y) in enumerate(trajectory_real):
            ax2.annotate(f'({x:.1f}, {y:.1f})m', (x, y), 
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=9, fontweight='bold')
        
        ax2.grid(True, alpha=0.5)
        ax2.set_xlabel('X (metros)')
        ax2.set_ylabel('Y (metros)')
        ax2.legend()
        
        # 3. Cálculos de distancia
        distances = []
        speeds = []
        
        for i in range(1, len(trajectory_real)):
            p1 = trajectory_real[i-1]
            p2 = trajectory_real[i]
            
            # Calcular distancia euclidiana
            distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            distances.append(distance)
            
            # Calcular velocidad
            time_diff = time_intervals[i] - time_intervals[i-1]
            speed_ms = distance / time_diff
            speed_kmh = speed_ms * 3.6
            speeds.append(speed_kmh)
        
        # Tabla de cálculos
        ax3.axis('off')
        ax3.set_title("3. Cálculos de Velocidad", fontsize=12, fontweight='bold')
        
        table_data = [
            ['Intervalo', 'Distancia (m)', 'Tiempo (s)', 'Velocidad (km/h)'],
            [f't0 → t1', f'{distances[0]:.2f}', f'{time_intervals[1]:.3f}', f'{speeds[0]:.1f}'],
            [f't1 → t2', f'{distances[1]:.2f}', f'{time_intervals[2] - time_intervals[1]:.3f}', f'{speeds[1]:.1f}'],
            ['', '', 'Promedio:', f'{np.mean(speeds):.1f}']
        ]
        
        table = ax3.table(cellText=table_data, cellLoc='center', loc='center',
                         colWidths=[0.2, 0.25, 0.2, 0.25])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 2)
        
        # Colorear header
        for i in range(4):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # 4. Gráfico de velocidad vs tiempo
        ax4.plot(time_intervals[1:], speeds, 'bo-', linewidth=2, markersize=8)
        ax4.set_title("4. Velocidad vs Tiempo", fontsize=12, fontweight='bold')
        ax4.set_xlabel('Tiempo (s)')
        ax4.set_ylabel('Velocidad (km/h)')
        ax4.grid(True, alpha=0.5)
        ax4.set_ylim(0, max(speeds) * 1.1)
        
        # Línea de velocidad promedio
        avg_speed = np.mean(speeds)
        ax4.axhline(y=avg_speed, color='red', linestyle='--', 
                   label=f'Promedio: {avg_speed:.1f} km/h')
        ax4.legend()
        
        plt.tight_layout()
        plt.savefig('examples/images/demo_3_calculo_velocidad.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("🚗 CÁLCULO DE VELOCIDAD:")
        print(f"   • Posiciones transformadas a coordenadas reales")
        print(f"   • Distancia total recorrida: {sum(distances):.2f} metros")
        print(f"   • Tiempo total: {time_intervals[-1]:.3f} segundos")
        print(f"   • Velocidad promedio: {np.mean(speeds):.1f} km/h")
        print(f"   • Fórmula: V = (distancia_metros / tiempo_segundos) * 3.6\n")
    
    def demo_4_matrix_visualization(self):
        """Visualiza la matriz de homografía"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Matriz de homografía
        ax1.axis('off')
        ax1.set_title("Matriz de Homografía (3x3)", fontsize=14, fontweight='bold')
        
        # Mostrar la matriz
        matrix_text = "H = \n"
        for i in range(3):
            row = "  [  "
            for j in range(3):
                row += f"{self.homography_matrix[i,j]:8.2e}  "
            row += "]\n"
            matrix_text += row
        
        ax1.text(0.1, 0.7, matrix_text, fontsize=12, fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
        
        # Explicación de la transformación
        explanation = """
                        Transformación de coordenadas:

                        [x']     [h11  h12  h13]   [x]
                        [y']  =  [h21  h22  h23] × [y]
                        [w']     [h31  h32  h33]   [1]

                        Donde:
                        • (x,y) = coordenadas en imagen
                        • (x',y') = coordenadas reales
                        • w' = factor de escala homogéneo

                        Coordenadas finales:
                        x_real = x'/w'
                        y_real = y'/w'
                        """
        
        ax2.axis('off')
        ax2.set_title("Fórmula de Transformación", fontsize=14, fontweight='bold')
        ax2.text(0.05, 0.95, explanation, fontsize=11, fontfamily='monospace',
                verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig('examples/images/demo_4_matriz_homografia.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print("🧮 MATRIZ DE HOMOGRAFÍA:")
        print("   • Matriz 3x3 que define la transformación perspectiva")
        print("   • Calculada usando cv2.findHomography()")
        print("   • Permite convertir cualquier punto (x,y) de imagen a metros reales")
        print("   • Es la base matemática de todo el sistema\n")
        
    def test_inverse_transform(self):
        """
        Prueba la transformación inversa para verificar la lógica de la matriz.
        """
        # Punto central del rectángulo en el mundo real (en metros)
        center_point_real = (self.real_width_m / 2, self.real_length_m / 2)
        
        # Necesitamos la matriz inversa para ir de metros -> píxeles
        inverse_homography_matrix = np.linalg.inv(self.homography_matrix)
        
        # Transformar el punto central real a coordenadas de la imagen
        point_real_np = np.array([[center_point_real]], dtype=np.float32)
        transformed_point_px = cv2.perspectiveTransform(point_real_np, inverse_homography_matrix)[0][0]
        
        # --- Visualización ---
        plt.figure(figsize=(10, 8))
        plt.imshow(self.original_image)
        
        # Dibujar el polígono de referencia
        polygon = patches.Polygon(self.image_points, linewidth=2, edgecolor='yellow', facecolor='yellow', alpha=0.3)
        plt.gca().add_patch(polygon)
        
        # Dibujar el punto transformado
        plt.plot(transformed_point_px[0], transformed_point_px[1], 'ro', markersize=12, label='Centro Real Proyectado')
        
        plt.title("Test de Transformación Inversa")
        plt.legend()
        plt.show()
        
        print("--- ANÁLISIS DEL TEST INVERSO ---")
        print(f"El punto central del mundo real ({center_point_real[0]:.1f}m, {center_point_real[1]:.1f}m)...")
        print(f"...se proyecta en la coordenada de imagen ({int(transformed_point_px[0])}, {int(transformed_point_px[1])})")
        print("El punto rojo debe caer DENTRO del área amarilla.")
    
    def run_complete_demo(self):
        """Ejecuta toda la demostración completa"""
        print("="*60)
        print("🎯 DEMOSTRACIÓN COMPLETA: CORRECCIÓN DE HOMOGRAFÍA")
        print("="*60)
        print()
        
        print("CONFIGURACIÓN:")
        print(f"   • Imagen: {self.image_path}")
        print(f"   • Puntos de referencia: {len(self.image_points)} puntos")
        print(f"   • Dimensiones reales: {self.real_width_m}m × {self.real_length_m}m")
        print(f"   • Resolución imagen: {self.width}×{self.height} píxeles")
        print()
        
        # Ejecutar todas las demostraciones
        self.demo_1_perspective_problem()
        input("Presiona Enter para continuar con la corrección de homografía...")
        
        self.test_inverse_transform()
        input("Presiona Enter para continuar con la corrección de homografía...")
        
        self.demo_2_homography_correction()
        input("Presiona Enter para continuar con el cálculo de velocidad...")
        
        self.demo_3_speed_calculation()
        input("Presiona Enter para ver la matriz de homografía...")
        
        self.demo_4_matrix_visualization()
        input("Presiona Enter para continuar con la corrección de homografía...")
        
        print("✅ DEMOSTRACIÓN COMPLETADA")
        print("   • Archivos guardados: demo_1_*.png, demo_2_*.png, etc.")
        print("   • Úsalos en tu video para explicar el concepto")


if __name__ == "__main__":
    example_params = {
        'image_path': 'examples/images/road.jpg',
        'image_points': [(775, 460), (975, 460), (980, 510), (755, 510)],
        'real_width_m': 3.3,
        'real_length_m': 3.0
    }
    
    print("🚀 EJECUTANDO DEMO CON PARÁMETROS DE EJEMPLO")
    print("   (Modifica los parámetros en el código o usa argumentos CLI)")
    print()
    
    try:
        demo = HomographyDemo(**example_params)
        demo.run_complete_demo()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Para usar tus propios datos:")
        print("python homography_demo.py --image tu_imagen.jpg --points '775,460,975,460,980,510,755,510' --width 3.3 --length 3.0")