"""
Démonstration du Projet de Compression BitPacking
Auteur: LOUNIS Elies
"""

from factory import BitPackingFactory
from timing import CompressionBenchmark
from benchmark import verify_correctness
import random


def exemple_compression_base():
    """Exemple simple de compression."""
    print("\n" + "="*60)
    print("EXEMPLE 1 : Compression de Base")
    print("="*60)
    
    factory = BitPackingFactory()
    compressor = factory.create("consecutive")
    
    # Données d'exemple
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    print(f"\nTableau original    : {data}")
    print(f"Taille originale    : {len(data) * 4} octets")
    
    # Compression
    compressed = compressor.compress(data)
    print(f"Taille compressée   : {len(compressed) * 4} octets")
    print(f"Ratio de compression: {(len(data) * 4) / (len(compressed) * 4):.2f}x")
    
    # Décompression
    decompressed = []
    compressor.decompress(compressed, decompressed)
    print(f"Décompression OK    : {decompressed == data}")


def exemple_overflow():
    """Exemple avec zone de débordement."""
    print("\n" + "="*60)
    print("EXEMPLE 2 : Compression avec Overflow")
    print("="*60)
    
    factory = BitPackingFactory()
    compressor = factory.create("overflow_consecutive")
    
    # Données avec outliers
    data = [1, 2, 3, 1024, 4, 5, 2048]
    print(f"\nTableau avec outliers: {data}")
    print("Note: 1024 et 2048 nécessitent beaucoup plus de bits")
    
    compressed = compressor.compress(data)
    print(f"\nZone overflow       : {compressor.overflow_area}")
    print(f"Indices overflow    : {compressor.overflow_indices}")
    
    decompressed = []
    compressor.decompress(compressed, decompressed)
    print(f"Décompression OK    : {decompressed == data}")


def exemple_negatifs():
    """Exemple avec nombres négatifs."""
    print("\n" + "="*60)
    print("EXEMPLE 3 : Nombres Négatifs")
    print("="*60)
    
    factory = BitPackingFactory()
    compressor = factory.create("consecutive")
    
    data = [-5, -3, -1, 0, 1, 3, 5]
    print(f"\nTableau avec négatifs: {data}")
    
    compressed = compressor.compress(data)
    decompressed = []
    compressor.decompress(compressed, decompressed)
    print(f"Décompression OK     : {decompressed == data}")
    print("\nNote: Encodage par offset utilisé pour les négatifs")


def exemple_performance():
    """Mesure de performance."""
    print("\n" + "="*60)
    print("EXEMPLE 4 : Mesures de Performance")
    print("="*60)
    
    random.seed(42)
    data = [random.randint(0, 100) for _ in range(1000)]
    
    factory = BitPackingFactory()
    benchmark = CompressionBenchmark()
    
    types = [
        ("Consecutive", "consecutive"),
        ("Non-Consecutive", "non_consecutive"),
        ("Overflow Consecutive", "overflow_consecutive"),
        ("Overflow Non-Consecutive", "overflow_non_consecutive")
    ]
    
    print(f"\nTest avec {len(data)} entiers aléatoires (0-100)")
    print("-" * 60)
    
    for nom, type_comp in types:
        try:
            compressor = factory.create(type_comp)
            results = benchmark.benchmark(compressor, data)
            
            print(f"\n{nom}:")
            print(f"  Compression   : {results['compression_time']['median']*1000:.2f} ms")
            print(f"  Décompression : {results['decompression_time']['median']*1000:.2f} ms")
            print(f"  Ratio         : {results['compression_ratio']:.2f}x")
            print(f"  Gain d'espace : {((1 - 1/results['compression_ratio'])*100):.1f}%")
        except Exception as e:
            print(f"\n{nom}: ERREUR - {e}")


def main():
    """Fonction principale."""
    print("\n" + "="*70)
    print("  PROJET : COMPRESSION D'ENTIERS PAR BIT PACKING")
    print("  Auteur : LOUNIS Elies")
    print("="*70)
    
    # Exemples de démonstration
    exemple_compression_base()
    exemple_overflow()
    exemple_negatifs()
    exemple_performance()
    
    # Vérification de la correction
    print("\n\n" + "="*60)
    print("VÉRIFICATION DE LA CORRECTION")
    print("="*60)
    verify_correctness()
    
    print("\n" + "="*70)
    print("  FIN DES DÉMONSTRATIONS")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

