"""
Module de Benchmark pour la Compression BitPacking
Auteur: LOUNIS Elies
"""

import random
from typing import List, Dict
from factory import BitPackingFactory, CompressionType
from timing import CompressionBenchmark


def generer_donnees(taille: int, intervalle: tuple = (0, 100), seed: int = None) -> List[int]:
    """Génère un tableau de données de test."""
    if seed is not None:
        random.seed(seed)
    return [random.randint(intervalle[0], intervalle[1]) for _ in range(taille)]


def afficher_resultats(results: Dict, nom: str):
    """Affiche les résultats de benchmark."""
    print(f"\n{'='*60}")
    print(f"{nom}")
    print(f"{'='*60}")
    
    print(f"\nCompression   : {results['compression_time']['median']*1000:.2f} ms")
    print(f"Décompression : {results['decompression_time']['median']*1000:.2f} ms")
    print(f"Accès direct  : {results['get_time']['median']*1000:.4f} ms")
    
    print(f"\nTaille originale  : {results['original_size_bytes']:,} octets")
    print(f"Taille compressée : {results['compressed_size_bytes']:,} octets")
    print(f"Ratio             : {results['compression_ratio']:.2f}x")
    print(f"Gain d'espace     : {((1 - 1/results['compression_ratio'])*100):.1f}%")


def verify_correctness():
    """Vérifie la correction des algorithmes de compression."""
    print("\n" + "="*60)
    print("TESTS DE CORRECTION")
    print("="*60)
    
    factory = BitPackingFactory()
    
    cas_tests = [
        ([1, 2, 3, 4, 5], "Nombres positifs simples"),
        ([1, 2, 3, 1024, 4, 5, 2048], "Avec valeurs grandes"),
        ([-5, -3, -1, 0, 1, 3, 5], "Avec nombres négatifs"),
        ([0] * 10, "Tous zéros"),
        ([100, 200, 300, 400, 500], "Valeurs moyennes"),
        (generer_donnees(100, (-100, 100), 42), "100 valeurs aléatoires"),
    ]
    
    types_compression = [
        CompressionType.CONSECUTIVE,
        CompressionType.NON_CONSECUTIVE,
        CompressionType.OVERFLOW_CONSECUTIVE,
        CompressionType.OVERFLOW_NON_CONSECUTIVE,
    ]
    
    tous_reussis = True
    
    for original, nom_test in cas_tests:
        print(f"\nTest : {nom_test} ({len(original)} éléments)")
        
        for type_comp in types_compression:
            try:
                compressor = factory.create_from_enum(type_comp)
                compressed = compressor.compress(original)
                decompressed = []
                compressor.decompress(compressed, decompressed)
                
                # Vérifier la décompression
                if decompressed == original:
                    print(f"  ✓ {type_comp.value}")
                    
                    # Vérifier l'accès direct
                    acces_ok = True
                    for i in range(len(original)):
                        if compressor.get(i) != original[i]:
                            print(f"    ✗ get({i}) échoué: attendu {original[i]}, obtenu {compressor.get(i)}")
                            acces_ok = False
                            tous_reussis = False
                            break
                    
                    if acces_ok:
                        print(f"    ✓ Accès direct OK")
                else:
                    print(f"  ✗ {type_comp.value} - Décompression incorrecte")
                    tous_reussis = False
                    
            except Exception as e:
                print(f"  ✗ {type_comp.value} - ERREUR : {e}")
                tous_reussis = False
    
    if tous_reussis:
        print("\n" + "="*60)
        print("✓ TOUS LES TESTS RÉUSSIS")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("✗ CERTAINS TESTS ONT ÉCHOUÉ")
        print("="*60)
    
    return tous_reussis


def benchmark_complet():
    """Exécute un benchmark complet."""
    print("="*60)
    print("BENCHMARK COMPLET")
    print("="*60)
    
    benchmark = CompressionBenchmark()
    factory = BitPackingFactory()
    
    scenarios = [
        ("Petites données uniformes", generer_donnees(100, (0, 50), 42)),
        ("Données moyennes uniformes", generer_donnees(1000, (0, 100), 42)),
        ("Grandes données uniformes", generer_donnees(10000, (0, 200), 42)),
        ("Avec nombres négatifs", generer_donnees(1000, (-100, 100), 42)),
    ]
    
    types_compression = [
        ("Consecutive", CompressionType.CONSECUTIVE),
        ("Non-Consecutive", CompressionType.NON_CONSECUTIVE),
        ("Overflow Consecutive", CompressionType.OVERFLOW_CONSECUTIVE),
        ("Overflow Non-Consecutive", CompressionType.OVERFLOW_NON_CONSECUTIVE),
    ]
    
    for nom_scenario, donnees_test in scenarios:
        print(f"\n{'#'*60}")
        print(f"SCÉNARIO : {nom_scenario} ({len(donnees_test)} éléments)")
        print(f"{'#'*60}")
        
        for nom_comp, type_comp in types_compression:
            try:
                compressor = factory.create_from_enum(type_comp)
                results = benchmark.benchmark(compressor, donnees_test)
                afficher_resultats(results, nom_comp)
            except Exception as e:
                print(f"\n{nom_comp} : ERREUR - {e}")


def analyse_latence():
    """Analyse du seuil de rentabilité de la compression."""
    print("\n\n" + "="*60)
    print("ANALYSE DE LA LATENCE RÉSEAU")
    print("="*60)
    
    benchmark = CompressionBenchmark()
    factory = BitPackingFactory()
    
    tailles = [1000, 10000]
    types = [
        ("Consecutive", CompressionType.CONSECUTIVE),
        ("Non-Consecutive", CompressionType.NON_CONSECUTIVE),
    ]
    
    bandes_passantes_mbps = [10, 100, 1000]
    
    for taille in tailles:
        print(f"\n{'#'*60}")
        print(f"Taille des données : {taille:,} entiers")
        print(f"{'#'*60}")
        
        donnees = generer_donnees(taille, (0, 100), 42)
        
        for nom, type_comp in types:
            try:
                compressor = factory.create_from_enum(type_comp)
                results = benchmark.benchmark(compressor, donnees)
                
                print(f"\n{nom} :")
                overhead = results['compression_time']['median'] + results['decompression_time']['median']
                print(f"  Temps compression+décompression : {overhead*1000:.2f} ms")
                print(f"  Ratio de compression            : {results['compression_ratio']:.2f}x")
                
                for bp in bandes_passantes_mbps:
                    temps_original = results['original_size_bytes'] / ((bp * 1_000_000) / 8)
                    temps_compresse = results['compressed_size_bytes'] / ((bp * 1_000_000) / 8)
                    gain_temps = temps_original - temps_compresse
                    benefice_net = gain_temps - overhead
                    
                    print(f"    @ {bp:4d} Mbps : bénéfice net = {benefice_net*1000:7.2f} ms", end="")
                    if benefice_net > 0:
                        print(f"  ✓ Compression avantageuse")
                    else:
                        print(f"  ✗ Overhead trop important")
                        
            except Exception as e:
                print(f"\n{nom} : ERREUR - {e}")


if __name__ == "__main__":
    # Vérification de la correction
    verify_correctness()
    
    # Benchmark complet
    benchmark_complet()
    
    # Analyse de la latence
    analyse_latence()
