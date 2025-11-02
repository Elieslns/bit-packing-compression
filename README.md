# Projet de Compression Bit Packing par Elies LOUNIS

## Description

Ce projet implémente différentes méthodes de compression d'arrays d'entiers basées sur le **Bit Packing**. L'objectif est de réduire le nombre de bits nécessaires pour transmettre des données entières sur le réseau, tout en conservant un accès direct aux éléments (sans décompression complète).

## Structure du Projet

```
.
├── bit_packing.py              # Implémentation de base du bit packing
├── bit_packing_overflow.py     # Compression avec zones de débordement
├── factory.py                  # Factory pattern pour créer les compresseurs
├── timing.py                   # Mesures de performance et timing
├── benchmark.py                # Benchmarks complets
├── main.py                     # Point d'entrée avec exemples
└── README.md                   # Ce fichier
```

## Types de Compression Implémentés

### 1. BitPackingConsecutive
Permet aux entiers compressés de s'étendre sur deux entiers consécutifs dans la sortie. Utilise l'espace de manière optimale.

**Exemple**: Si 6 éléments nécessitent 12 bits chacun:
- Les 2 premiers éléments dans le premier entier (24 bits)
- Le 3ème élément sur les bits 25-32 du premier entier + bits 1-4 du deuxième
- Et ainsi de suite...

### 2. BitPackingNonConsecutive
Les entiers compressés ne s'étendent jamais sur deux entiers consécutifs. Chaque élément compressé tient dans un seul entier de sortie.

**Exemple**: Si 6 éléments nécessitent 12 bits chacun:
- 2 éléments par entier (12 bits chacun, 24 bits au total)
- 3 entiers nécessaires au total

### 3. BitPackingOverflow
Utilise des zones de débordement pour les valeurs qui nécessitent beaucoup plus de bits que la majorité. Un bit de drapeau indique si la valeur est stockée directement ou fait référence à la zone de débordement.

**Exemple**: Pour [1, 2, 3, 1024, 4, 5, 2048]:
- 1, 2, 3, 4, 5 sont encodés avec 3 bits
- 1024 et 2048 vont dans la zone de débordement
- Encodage: `0-1, 0-2, 0-3, 1-0, 0-4, 0-5, 1-1` suivi de `[1024, 2048]`

## API Principale

### Factory Pattern

```python
from factory import BitPackingFactory

factory = BitPackingFactory()

# Créer un compresseur
compressor = factory.create("consecutive")
compressor = factory.create("non_consecutive")
compressor = factory.create("overflow_consecutive")
compressor = factory.create("overflow_non_consecutive")
```

### Compression/Decompression

```python
# Compresser un array
data = [1, 2, 3, 4, 5]
compressed = compressor.compress(data)

# Décompresser
result = []
compressor.decompress(compressed, result)

# Accès direct (sans décompression complète)
value = compressor.get(2)  # Retourne data[2]
```

### Mesure de Performance

```python
from timing import CompressionBenchmark

benchmark = CompressionBenchmark()
results = benchmark.benchmark(compressor, data)

print(f"Temps de compression: {results['compression_time']['median']*1000:.2f} ms")
print(f"Ratio de compression: {results['compression_ratio']:.2f}x")
```

## Utilisation

### Exécuter les exemples

```bash
python main.py
```

### Lancer les benchmarks complets

```bash
python benchmark.py
```

## Protocole de Mesure de Performance

Le système de mesure utilise plusieurs techniques pour garantir la précision:

1. **Warm-up runs**: Exécutions d'échauffement pour stabiliser le système (cache, etc.)
2. **Multiple iterations**: Plusieurs exécutions pour la fiabilité statistique
3. **Médiane et moyenne**: Filtrage des valeurs aberrantes
4. **High-resolution timer**: Utilisation de `time.perf_counter()` pour la précision

### Calcul de la Latence Break-Even

La compression est avantageuse quand:
```
t_compression + t_decompression + t_transmission_compressé < t_transmission_non_compressé
```

Note: La latence réseau s'annule dans la comparaison car elle est identique dans les deux cas.

## Gestion des Nombres Négatifs

### Problème

Les nombres négatifs en complément à deux peuvent nécessiter tous les bits disponibles (ex: -1 = 11111111 en 8 bits), rendant la compression inefficace.

### Solution Implémentée

**Encodage par offset**:
- Pour k bits, on représente les valeurs de -2^(k-1)+1 à 2^(k-1)-1
- Valeur ≥ 0: stockée directement
- Valeur < 0: encodée comme `2^(k-1) + abs(valeur)`
- Décodage: si valeur > 2^(k-1)-1, alors valeur = -(valeur - 2^(k-1))

**Exemple avec 3 bits** (peut représenter -3 à 3):
- -3 → 7 (4+3)
- -2 → 6 (4+2)
- -1 → 5 (4+1)
- 0 → 0
- 1 → 1
- 2 → 2
- 3 → 3

### Avantages
- Permet de compresser efficacement les petits nombres négatifs
- Conserve l'accès direct (méthode `get()`)
- Compatible avec tous les types de compression
- Pas de perte d'information

### Alternatives Considérées

1. **ZigZag encoding** (Protocol Buffers): Plus efficace mais plus complexe
2. **Stockage séparé du signe**: Nécessite une structure supplémentaire, perte d'accès direct

## Benchmarks et Résultats

Les benchmarks incluent:

1. **Tests de correctitude**: Vérification que compression/décompression préserve les données
2. **Tests de performance**: Temps d'exécution pour différentes tailles de données
3. **Tests de compression ratio**: Efficacité de la compression
4. **Analyse de latence**: Seuil où la compression devient avantageuse

Scénarios testés:
- Petites données uniformes (100 éléments)
- Moyennes données uniformes (1000 éléments)
- Grandes données uniformes (10000 éléments)
- Scénarios avec overflow (quelques grandes valeurs)
- Données avec nombres négatifs
- Données mixtes

## Exigences

- Python 3.7+
- Modules standards uniquement (pas de dépendances externes)

## Auteur

**Nom** : LOUNIS Elies


