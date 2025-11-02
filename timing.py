"""
Mesure de Temps et de Performance

Ce module fournit des utilitaires pour mesurer avec précision le temps d'exécution
des opérations de compression et décompression.
"""

import time
import statistics
from typing import Callable, List, Dict, Tuple, Any
from contextlib import contextmanager


class TimingProtocol:
    """
    Protocole pour mesurer le temps d'exécution avec une haute précision.
    
    Utilise plusieurs techniques pour minimiser la surcharge de mesure :
    - Exécutions d'échauffement pour stabiliser l'état du système
    - Itérations multiples pour la fiabilité statistique
    - Calcul médiane/moyenne pour filtrer les valeurs aberrantes
    """
    
    def __init__(self, warmup_runs: int = 3, measurement_runs: int = 10):
        """
        Initialise le protocole de mesure de temps.
        
        Args:
            warmup_runs: Nombre d'exécutions d'échauffement pour stabiliser le système
            measurement_runs: Nombre d'exécutions de mesure pour les statistiques
        """
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
    
    @contextmanager
    def _measure_time(self):
        """Gestionnaire de contexte pour la mesure du temps utilisant un timer haute résolution."""
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            return end - start
    
    def measure(self, func: Callable, *args, **kwargs) -> Dict[str, float]:
        """
        Mesure le temps d'exécution d'une fonction.
        
        Args:
            func: Fonction à mesurer
            *args: Arguments positionnels pour func
            **kwargs: Arguments nommés pour func
        
        Returns:
            Dictionnaire avec les statistiques de temps :
            - 'median': Temps d'exécution médian en secondes
            - 'mean': Temps d'exécution moyen en secondes
            - 'min': Temps d'exécution minimum en secondes
            - 'max': Temps d'exécution maximum en secondes
            - 'stdev': Écart-type en secondes
            - 'total': Temps total pour toutes les exécutions en secondes
        """
        # Exécutions d'échauffement pour stabiliser le système (cache, JIT, etc.)
        for _ in range(self.warmup_runs):
            try:
                func(*args, **kwargs)
            except Exception:
                pass  # Ignorer les erreurs pendant l'échauffement
        
        # Exécutions de mesure
        times = []
        for _ in range(self.measurement_runs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                raise RuntimeError(f"Erreur pendant la mesure de temps : {e}")
            end = time.perf_counter()
            times.append(end - start)
        
        return {
            'median': statistics.median(times),
            'mean': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'stdev': statistics.stdev(times) if len(times) > 1 else 0.0,
            'total': sum(times),
            'runs': len(times)
        }
    
    def measure_compress(self, compressor, array: List[int]) -> Dict[str, float]:
        """Mesure le temps de compression."""
        def compress_op():
            return compressor.compress(array)
        return self.measure(compress_op)
    
    def measure_decompress(self, compressor, compressed: List[int]) -> Dict[str, float]:
        """Mesure le temps de décompression."""
        def decompress_op():
            result = []
            compressor.decompress(compressed, result)
            return result
        return self.measure(decompress_op)
    
    def measure_get(self, compressor, indices: List[int]) -> Dict[str, float]:
        """Mesure le temps pour les opérations d'accès aléatoire get."""
        def get_ops():
            for i in indices:
                compressor.get(i)
        return self.measure(get_ops)
    
    def measure_transmission_time(self, data_size_bytes: int, latency_ms: float,
                                 bandwidth_mbps: float = 100.0) -> float:
        """
        Calcule le temps de transmission théorique.
        
        Args:
            data_size_bytes: Taille des données à transmettre en octets
            latency_ms: Latence réseau en millisecondes
            bandwidth_mbps: Bande passante en mégabits par seconde
        
        Returns:
            Temps de transmission total en secondes
        """
        # Convertir la bande passante en octets par seconde
        bandwidth_bytes_per_sec = (bandwidth_mbps * 1_000_000) / 8
        
        # Temps de transmission = latence + taille_données / bande_passante
        transmission_time = (latency_ms / 1000.0) + (data_size_bytes / bandwidth_bytes_per_sec)
        
        return transmission_time


class CompressionBenchmark:
    """
    Benchmark complet pour les algorithmes de compression.
    """
    
    def __init__(self, timing_protocol: TimingProtocol = None):
        """
        Initialise le benchmark.
        
        Args:
            timing_protocol: Protocole de mesure personnalisé. Si None, utilise la valeur par défaut.
        """
        self.timing = timing_protocol or TimingProtocol()
    
    def benchmark(self, compressor, array: List[int]) -> Dict[str, Any]:
        """
        Exécute un benchmark complet pour un compresseur.
        
        Args:
            compressor: Instance BitPackingBase
            array: Tableau d'entrée à compresser
        
        Returns:
            Dictionnaire avec les résultats du benchmark :
            - 'compression_time': Statistiques de temps pour la compression
            - 'decompression_time': Statistiques de temps pour la décompression
            - 'get_time': Statistiques de temps pour l'accès aléatoire
            - 'compression_ratio': Ratio de la taille originale à la taille compressée
            - 'compressed_size_bytes': Taille des données compressées
            - 'original_size_bytes': Taille des données originales
        """
        # Mesurer la compression
        compressed = compressor.compress(array)
        compress_timing = self.timing.measure_compress(compressor, array)
        
        # Mesurer la décompression
        result = []
        decompress_timing = self.timing.measure_decompress(compressor, compressed)
        
        # Mesurer l'accès aléatoire (échantillon d'indices)
        sample_indices = [i for i in range(0, len(array), max(1, len(array) // 10))]
        get_timing = self.timing.measure_get(compressor, sample_indices)
        
        # Calculer les tailles
        original_size = len(array) * 4  # En supposant des entiers 32 bits
        compressed_size = len(compressed) * 4
        
        return {
            'compression_time': compress_timing,
            'decompression_time': decompress_timing,
            'get_time': get_timing,
            'compression_ratio': original_size / compressed_size if compressed_size > 0 else 0,
            'compressed_size_bytes': compressed_size,
            'original_size_bytes': original_size,
            'compressed_length': len(compressed),
            'original_length': len(array)
        }
    
    def find_break_even_latency(self, compressor, array: List[int],
                               bandwidth_mbps: float = 100.0) -> Dict[str, float]:
        """
        Calcule l'analyse du temps de transmission pour compression vs non compressé.
        
        Note : La latence s'annule dans la comparaison :
        - Non compressé : latence + temps_transmission
        - Compressé : temps_compression + temps_décompression + latence + temps_transmission
        
        Donc la compression est avantageuse quand :
        temps_compression + temps_décompression + temps_transmission_compressé < temps_transmission_non_compressé
        
        Args:
            compressor: Instance BitPackingBase
            array: Tableau d'entrée à compresser
            bandwidth_mbps: Bande passante réseau en mégabits par seconde
        
        Returns:
            Dictionnaire avec les résultats d'analyse :
            - 'compression_overhead': Temps total compression/décompression (ms)
            - 'time_saved_transmission': Temps économisé en transmission (ms)
            - 'net_benefit': Bénéfice net de la compression (ms)
            - 'is_beneficial': Si la compression est bénéfique à cette bande passante
        """
        # Benchmark de la compression
        results = self.benchmark(compressor, array)
        
        compress_time = results['compression_time']['median']
        decompress_time = results['decompression_time']['median']
        overhead = compress_time + decompress_time
        
        original_size = results['original_size_bytes']
        compressed_size = results['compressed_size_bytes']
        
        # Calculer les temps de transmission
        bandwidth_bytes_per_sec = (bandwidth_mbps * 1_000_000) / 8
        transmission_time_original = original_size / bandwidth_bytes_per_sec
        transmission_time_compressed = compressed_size / bandwidth_bytes_per_sec
        
        # Temps économisé en transmission
        time_saved_transmission = transmission_time_original - transmission_time_compressed
        
        # Bénéfice net
        net_benefit = time_saved_transmission - overhead
        
        return {
            'compression_overhead': overhead * 1000,  # ms
            'time_saved_transmission': time_saved_transmission * 1000,  # ms
            'net_benefit': net_benefit * 1000,  # ms
            'is_beneficial': net_benefit > 0,
            'total_time_uncompressed': (transmission_time_original) * 1000,  # ms
            'total_time_compressed': (overhead + transmission_time_compressed) * 1000,  # ms
        }
    
    def compare_methods(self, compressors: Dict[str, Any], array: List[int]) -> Dict[str, Any]:
        """
        Compare plusieurs méthodes de compression.
        
        Args:
            compressors: Dictionnaire associant des noms à des instances BitPackingBase
            array: Tableau d'entrée à tester
        
        Returns:
            Dictionnaire avec les résultats de comparaison pour chaque compresseur
        """
        results = {}
        for name, compressor in compressors.items():
            results[name] = self.benchmark(compressor, array)
        return results

