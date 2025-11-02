"""
BitPacking avec Zones de Débordement

Ce module implémente la compression bit packing avec des zones de débordement.
Quand certaines valeurs nécessitent significativement plus de bits que d'autres, on utilise
une zone de débordement pour stocker les grandes valeurs séparément, permettant au tableau
principal d'utiliser moins de bits par élément.
"""

import math
from typing import List, Tuple
from bit_packing import BitPackingBase


class BitPackingOverflow(BitPackingBase):
    """
    Compression bit packing avec zones de débordement.
    
    Les valeurs qui nécessitent plus de bits que le cas général sont stockées dans
    une zone de débordement, et une référence (avec un bit de drapeau) est stockée dans
    le tableau compressé principal à la place.
    """
    
    def __init__(self, allow_consecutive: bool = True):
        """
        Initialise le compresseur bit packing avec débordement.
        
        Args:
            allow_consecutive: Si True, permet aux valeurs compressées de s'étendre
                             sur des entiers consécutifs (comme BitPackingConsecutive).
                             Si False, les valeurs compressées ne s'étendent jamais (comme BitPackingNonConsecutive).
        """
        super().__init__()
        self.allow_consecutive = allow_consecutive
        self.overflow_area: List[int] = []
        self.overflow_indices: List[int] = []  # Positions des valeurs de débordement dans le tableau original
        self.bits_for_overflow_index: int = 0
        self.value_bits: int = 0  # Bits pour les valeurs régulières (excluant le bit de drapeau)
    
    def compress(self, array: List[int]) -> List[int]:
        """
        Compresse un tableau d'entiers avec des zones de débordement.
        
        Algorithme:
        1. Identifier les valeurs qui nécessitent significativement plus de bits
        2. Calculer l'allocation optimale de bits pour les valeurs régulières
        3. Stocker les valeurs de débordement dans une zone séparée
        4. Utiliser un bit de drapeau pour indiquer si la valeur est directe ou une référence de débordement
        """
        if not array:
            return []
        
        self.original_length = len(array)
        
        # Trouver l'allocation optimale de bits
        regular_values, overflow_values, overflow_positions = self._classify_values(array)
        
        if not regular_values:
            # Toutes les valeurs vont dans le débordement
            self.overflow_area = overflow_values
            self.overflow_indices = list(range(len(array)))
            self.value_bits = 1  # Juste le bit de drapeau
            self.bits_for_overflow_index = self._calculate_bits_for_indices(len(overflow_values))
            self.has_negative_numbers = any(x < 0 for x in array)
        else:
            self.value_bits = self._calculate_bits_needed(regular_values)
            self.overflow_area = overflow_values
            self.overflow_indices = overflow_positions
            self.bits_for_overflow_index = self._calculate_bits_for_indices(len(overflow_values)) if overflow_values else 0
            self.has_negative_numbers = any(x < 0 for x in regular_values)
        
        # Bits totaux par élément : 1 bit de drapeau + value_bits OU bits_for_overflow_index
        total_bits = 1 + max(self.value_bits, self.bits_for_overflow_index)
        
        # Compresser le tableau
        compressed = []
        overflow_map = {pos: idx for idx, pos in enumerate(self.overflow_indices)}
        
        if self.allow_consecutive:
            compressed = self._compress_consecutive(array, total_bits, overflow_map)
        else:
            compressed = self._compress_non_consecutive(array, total_bits, overflow_map)
        
        # Ajouter les métadonnées et la zone de débordement à la fin des données compressées
        # Format : [données_compressées..., 0xFFFFFFFF (marqueur), original_length, taille_overflow, 
        #           bits_value, bits_overflow_idx, nb_indices, valeur1, valeur2, ...]
        # Toujours ajouter les métadonnées pour permettre la décompression indépendante
        # Utiliser 0xFFFFFFFF comme marqueur pour indiquer la présence de métadonnées
        compressed.append(0xFFFFFFFF)  # Marqueur spécial
        compressed.append(self.original_length)  # Taille originale
        compressed.append(len(self.overflow_area))  # Taille de l'overflow (peut être 0)
        compressed.append(self.value_bits)  # Bits pour les valeurs régulières
        compressed.append(self.bits_for_overflow_index)  # Bits pour les indices overflow
        compressed.append(len(self.overflow_indices) if self.overflow_indices else 0)  # Nombre d'indices
        if self.overflow_area:
            compressed.extend(self.overflow_area)  # Les valeurs de débordement
        
        self.compressed_data = compressed
        return compressed
    
    def _classify_values(self, array: List[int]) -> Tuple[List[int], List[int], List[int]]:
        """
        Classe les valeurs en régulières et débordement.
        
        Stratégie : Calculer les bits nécessaires pour toutes les valeurs. S'il y a un grand écart
        entre la majorité et les valeurs aberrantes, utiliser le débordement pour les valeurs aberrantes.
        """
        if not array:
            return [], [], []
        
        # Calculer les bits nécessaires pour chaque valeur
        bits_required = []
        for val in array:
            abs_val = abs(val)
            if abs_val == 0:
                bits_required.append(1)
            else:
                bits_required.append(math.floor(math.log2(abs_val)) + 1)
        
        # Trouver la médiane et l'utiliser comme référence
        sorted_bits = sorted(bits_required)
        median_bits = sorted_bits[len(sorted_bits) // 2]
        
        # Les valeurs nécessitant plus que médiane + seuil vont dans le débordement
        threshold = max(3, median_bits // 2)  # Au moins 3 bits de différence
        overflow_threshold = median_bits + threshold
        
        regular_values = []
        overflow_values = []
        overflow_positions = []
        
        for i, (val, bits) in enumerate(zip(array, bits_required)):
            if bits > overflow_threshold:
                overflow_values.append(val)
                overflow_positions.append(i)
            else:
                regular_values.append(val)
        
        # Si la zone de débordement est trop grande, ça ne vaut pas le coup
        # N'utiliser le débordement que s'il économise de l'espace ou si le ratio est raisonnable
        if overflow_values:
            total_without_overflow = max(bits_required) * len(array)
            regular_bits = max([math.floor(math.log2(abs(x))) + 1 if x != 0 else 1 
                              for x in regular_values], default=1)
            bits_for_index = self._calculate_bits_for_indices(len(overflow_values))
            # Calculer avec le bit de drapeau inclus
            total_with_overflow = (regular_bits + 1) * len(array) + len(overflow_values) * 32
            
            # Utiliser l'overflow si :
            # 1. Il économise de l'espace, OU
            # 2. Le nombre de valeurs overflow est petit par rapport à la taille totale (< 30%)
            overflow_ratio = len(overflow_values) / len(array)
            space_saved = total_without_overflow - total_with_overflow
            
            # Si le débordement n'économise pas beaucoup d'espace ET qu'il y a trop de valeurs overflow, ne pas l'utiliser
            if space_saved < 0 and overflow_ratio > 0.3:
                return array, [], []
        
        return regular_values, overflow_values, overflow_positions
    
    def _calculate_bits_for_indices(self, num_overflow: int) -> int:
        """Calcule le nombre de bits nécessaires pour représenter les indices de débordement."""
        if num_overflow == 0:
            return 0
        if num_overflow == 1:
            return 1
        return math.floor(math.log2(num_overflow)) + 1
    
    def _compress_consecutive(self, array: List[int], total_bits: int, 
                             overflow_map: dict) -> List[int]:
        """Compresse avec extension sur entiers consécutifs autorisée."""
        compressed = []
        current_integer = 0
        current_bit_position = 0
        
        for i, value in enumerate(array):
            if i in overflow_map:
                # Valeur de débordement : drapeau=1, index dans la zone de débordement
                overflow_idx = overflow_map[i]
                flag_bit = 1
                
                # Écrire séparément : d'abord le flag (1 bit), puis l'index (bits_for_overflow_index bits)
                # Format: [flag][index] où flag est le LSB
                # Écrire le flag d'abord
                current_integer = self._set_bits(current_integer, flag_bit, current_bit_position, 1)
                current_bit_position += 1
                if current_bit_position >= 32:
                    compressed.append(current_integer)
                    current_integer = 0
                    current_bit_position = 0
                
                # Puis écrire l'index (peut s'étendre sur plusieurs entiers)
                bits_to_write = self.bits_for_overflow_index
                while bits_to_write > 0:
                    bits_available = 32 - current_bit_position
                    bits_to_write_now = min(bits_to_write, bits_available)
                    
                    # Extraire les bits de poids faible à écrire maintenant
                    bits_to_write_value = (overflow_idx >> (bits_to_write - bits_to_write_now)) & ((1 << bits_to_write_now) - 1)
                    
                    current_integer = self._set_bits(
                        current_integer,
                        bits_to_write_value,
                        current_bit_position,
                        bits_to_write_now
                    )
                    
                    current_bit_position += bits_to_write_now
                    bits_to_write -= bits_to_write_now
                    
                    if current_bit_position >= 32:
                        compressed.append(current_integer)
                        current_integer = 0
                        current_bit_position = 0
            else:
                # Valeur régulière : drapeau=0, valeur réelle
                flag_bit = 0
                value_to_write = value
                if self.has_negative_numbers and value < 0:
                    value_to_write = (1 << (self.value_bits - 1)) + abs(value)
                
                # Écrire séparément : d'abord le flag (1 bit), puis la valeur (value_bits bits)
                # Format: [flag][valeur] où flag est le LSB
                # Écrire le flag d'abord
                current_integer = self._set_bits(current_integer, flag_bit, current_bit_position, 1)
                current_bit_position += 1
                if current_bit_position >= 32:
                    compressed.append(current_integer)
                    current_integer = 0
                    current_bit_position = 0
                
                # Puis écrire la valeur (peut s'étendre sur plusieurs entiers)
                bits_to_write = self.value_bits
                while bits_to_write > 0:
                    bits_available = 32 - current_bit_position
                    bits_to_write_now = min(bits_to_write, bits_available)
                    
                    # Extraire les bits de poids faible à écrire maintenant
                    bits_to_write_value = (value_to_write >> (bits_to_write - bits_to_write_now)) & ((1 << bits_to_write_now) - 1)
                    
                    current_integer = self._set_bits(
                        current_integer,
                        bits_to_write_value,
                        current_bit_position,
                        bits_to_write_now
                    )
                    
                    current_bit_position += bits_to_write_now
                    bits_to_write -= bits_to_write_now
                    
                    if current_bit_position >= 32:
                        compressed.append(current_integer)
                        current_integer = 0
                        current_bit_position = 0
        
        if current_bit_position > 0:
            compressed.append(current_integer)
        
        return compressed
    
    def _compress_non_consecutive(self, array: List[int], total_bits: int,
                                  overflow_map: dict) -> List[int]:
        """
        Compresse sans extension sur entiers consécutifs.
        
        Principe : Chaque élément a une taille variable (flag + données).
        Avant d'écrire un élément, on vérifie s'il tient complètement dans l'entier actuel.
        Si non, on passe au prochain entier (l'élément ne sera jamais divisé entre deux entiers).
        """
        compressed = []
        elements_per_integer = 32 // total_bits
        current_integer = 0
        current_bit_position = 0
        elements_in_current = 0
        
        for i, value in enumerate(array):
            # Calculer la taille réelle de l'élément (flag + données)
            if i in overflow_map:
                element_size = 1 + self.bits_for_overflow_index  # Ex: 1 + 1 = 2 bits
            else:
                element_size = 1 + self.value_bits  # Ex: 1 + 9 = 10 bits
            
            # Vérifier si l'élément tient dans l'entier actuel
            # Si bit_pos + taille > 32, l'élément doit être écrit dans un nouvel entier
            if current_bit_position + element_size > 32:
                # Sauvegarder l'entier actuel et recommencer au bit 0 du prochain entier
                compressed.append(current_integer)
                current_integer = 0
                current_bit_position = 0
                elements_in_current = 0
            
            if i in overflow_map:
                # Valeur de débordement
                overflow_idx = overflow_map[i]
                flag_bit = 1
                # Écrire le flag
                current_integer = self._set_bits(current_integer, flag_bit, current_bit_position, 1)
                current_bit_position += 1
                
                # Puis écrire l'index
                current_integer = self._set_bits(
                    current_integer,
                    overflow_idx,
                    current_bit_position,
                    self.bits_for_overflow_index
                )
                current_bit_position += self.bits_for_overflow_index
            else:
                # Valeur régulière
                flag_bit = 0
                value_to_write = value
                if self.has_negative_numbers and value < 0:
                    value_to_write = (1 << (self.value_bits - 1)) + abs(value)
                
                # Écrire séparément : d'abord le flag (1 bit), puis la valeur (value_bits bits)
                # Format: [flag][valeur] où flag est le LSB
                current_integer = self._set_bits(current_integer, flag_bit, current_bit_position, 1)
                current_bit_position += 1
                
                # Puis écrire la valeur
                current_integer = self._set_bits(
                    current_integer,
                    value_to_write,
                    current_bit_position,
                    self.value_bits
                )
                current_bit_position += self.value_bits
            
            elements_in_current += 1
        
        if elements_in_current > 0:
            compressed.append(current_integer)
        
        return compressed
    
    def decompress(self, compressed: List[int], result: List[int]) -> None:
        """Décompresse les données compressées dans le tableau résultat."""
        if not compressed:
            return
        
        # Extraire les métadonnées et la zone de débordement depuis la fin des données compressées
        # Format : [données_compressées..., 0xFFFFFFFF (marqueur), original_length, taille_overflow,
        #           bits_value, bits_overflow_idx, nb_indices, valeur1, valeur2, ...]
        # Chercher le marqueur 0xFFFFFFFF depuis la fin
        overflow_found = False
        if len(compressed) >= 6:  # Minimum : marqueur + 5 métadonnées
            # Chercher le marqueur depuis la fin
            for i in range(len(compressed) - 1, max(-1, len(compressed) - 100), -1):
                if compressed[i] == 0xFFFFFFFF:
                    # Marqueur trouvé, vérifier les métadonnées qui suivent
                    if i + 5 < len(compressed):
                        original_len = compressed[i + 1]
                        overflow_size = compressed[i + 2]
                        value_bits_meta = compressed[i + 3]
                        bits_overflow_meta = compressed[i + 4]
                        nb_indices_meta = compressed[i + 5]
                        
                        # Vérifier la validité des métadonnées (overflow_size peut être 0)
                        if (original_len > 0 and original_len < 1000000 and
                            overflow_size >= 0 and overflow_size < 1000 and
                            value_bits_meta > 0 and value_bits_meta <= 32 and
                            bits_overflow_meta >= 0 and bits_overflow_meta <= 32 and
                            nb_indices_meta >= 0 and (overflow_size == 0 or nb_indices_meta <= overflow_size) and
                            i + 6 + overflow_size <= len(compressed)):
                            # Métadonnées valides, extraire
                            self.original_length = original_len
                            self.value_bits = value_bits_meta
                            self.bits_for_overflow_index = bits_overflow_meta
                            if overflow_size > 0:
                                self.overflow_area = compressed[i + 6:i + 6 + overflow_size]
                            else:
                                self.overflow_area = []
                            compressed = compressed[:i]  # Enlever les métadonnées
                            overflow_found = True
                            break
        
        # Si pas de métadonnées trouvées, on ne peut pas décompresser sans connaître original_length
        if not overflow_found:
            return
        
        result.clear()
        total_bits = 1 + max(self.value_bits, self.bits_for_overflow_index)
        
        if self.allow_consecutive:
            self._decompress_consecutive(compressed, total_bits, result)
        else:
            self._decompress_non_consecutive(compressed, total_bits, result)
        
        self.compressed_data = compressed
    
    def _decompress_consecutive(self, compressed: List[int], total_bits: int, 
                                result: List[int]) -> None:
        """Décompresse avec extension sur entiers consécutifs."""
        current_bit_position = 0
        current_integer_index = 0
        
        # Reconstruire overflow_indices pour savoir quels éléments sont overflow
        # On ne peut pas le savoir à l'avance, donc on doit lire le flag d'abord
        # et ajuster la taille en conséquence
        element_index = 0
        overflow_indices_reconstructed = []
        
        for _ in range(self.original_length):
            # Lire d'abord le flag (1 bit) pour déterminer la taille de l'élément
            flag = self._read_bits_consecutive(compressed, 1,
                                              current_bit_position, current_integer_index)
            current_bit_position, current_integer_index = self._advance_position(
                current_bit_position, current_integer_index, 1)
            
            if flag == 1:
                # Valeur de débordement : lire l'index (bits_for_overflow_index bits)
                overflow_idx = self._read_bits_consecutive(compressed, self.bits_for_overflow_index,
                                                          current_bit_position, current_integer_index)
                current_bit_position, current_integer_index = self._advance_position(
                    current_bit_position, current_integer_index, self.bits_for_overflow_index)
                
                overflow_idx = overflow_idx & ((1 << self.bits_for_overflow_index) - 1)
                overflow_indices_reconstructed.append(element_index)
                
                if overflow_idx < len(self.overflow_area):
                    result.append(self.overflow_area[overflow_idx])
                else:
                    result.append(0)  # Valeur par défaut
            else:
                # Valeur régulière : lire la valeur (value_bits bits)
                # On lit value_bits bits qui correspondent aux bits 1 à value_bits de encoded_value
                # (le flag a déjà été lu)
                value = self._read_bits_consecutive(compressed, self.value_bits,
                                                   current_bit_position, current_integer_index)
                current_bit_position, current_integer_index = self._advance_position(
                    current_bit_position, current_integer_index, self.value_bits)
                
                # Les bits lus sont déjà la partie valeur (bits 1 à value_bits de encoded_value)
                # Il faut juste s'assurer qu'on ne lit pas plus que value_bits bits
                value = value & ((1 << self.value_bits) - 1)
                
                # Décoder les nombres négatifs
                if self.has_negative_numbers:
                    threshold = 1 << (self.value_bits - 1)
                    max_positive = threshold - 1
                    if value > max_positive:
                        value = -(value - threshold)
                
                result.append(value)
            
            element_index += 1
        
        # Sauvegarder les indices reconstruits
        self.overflow_indices = overflow_indices_reconstructed
    
    def _decompress_non_consecutive(self, compressed: List[int], total_bits: int,
                                    result: List[int]) -> None:
        """
        Décompresse sans extension sur entiers consécutifs.
        
        Principe : Pour lire l'élément à l'index i, on doit parcourir tous les éléments
        précédents pour calculer sa position, car chaque élément a une taille variable.
        
        Algorithme :
        1. Pour chaque élément précédent, lire son flag pour connaître sa taille réelle
        2. Vérifier si cet élément aurait dû être écrit dans un nouvel entier
           (même logique que lors de la compression : si pos_before + taille > 32)
        3. Mettre à jour la position en conséquence
        4. Lire l'élément i en utilisant la même logique
        """
        # OPTIMISATION : Maintenir bit_pos et int_idx entre les itérations au lieu de recalculer O(n²) -> O(n)
        bit_pos = 0
        int_idx = 0
        
        for i in range(self.original_length):
            # Sauvegarder la position AVANT de lire le flag
            pos_before = bit_pos
            idx_before = int_idx
            
            # Lire le flag pour connaître la taille réelle de l'élément i
            flag = self._read_bits_consecutive(compressed, 1, bit_pos, int_idx)
            
            if flag == 1:
                element_data_size = self.bits_for_overflow_index
            else:
                element_data_size = self.value_bits
            
            element_total_size = 1 + element_data_size
            
            # Vérifier si l'élément i a été écrit dans un nouvel entier
            if pos_before + element_total_size > 32:
                # L'élément i est dans le prochain entier, repositionner et relire le flag
                int_idx = idx_before + 1
                bit_pos = 0
                flag = self._read_bits_consecutive(compressed, 1, bit_pos, int_idx)
                bit_pos = 1  # Positionner après le flag
            else:
                # L'élément i est dans l'entier actuel
                bit_pos = pos_before + 1  # Positionner après le flag
            
            if flag == 1:
                overflow_idx = self._read_bits_consecutive(compressed,
                                                          self.bits_for_overflow_index,
                                                          bit_pos, int_idx)
                overflow_idx = overflow_idx & ((1 << self.bits_for_overflow_index) - 1)
                    
                if overflow_idx < len(self.overflow_area):
                    result.append(self.overflow_area[overflow_idx])
                else:
                    result.append(0)
            else:
                value = self._read_bits_consecutive(compressed, self.value_bits,
                                                   bit_pos, int_idx)
                value = value & ((1 << self.value_bits) - 1)
                
                if self.has_negative_numbers:
                    threshold = 1 << (self.value_bits - 1)
                    max_positive = threshold - 1
                    if value > max_positive:
                        value = -(value - threshold)
                
                result.append(value)
            
            # Avancer la position pour le prochain élément
            element_total_size = 1 + element_data_size
            if pos_before + element_total_size > 32:
                int_idx = idx_before + 1
                bit_pos = element_total_size
            else:
                bit_pos = pos_before + element_total_size
                if bit_pos >= 32:
                    int_idx = idx_before + 1
                    bit_pos = 0
    
    def _read_bits_consecutive(self, compressed: List[int], num_bits: int,
                              start_bit: int, start_index: int) -> int:
        """Lit les bits qui peuvent s'étendre sur des entiers consécutifs."""
        value = 0
        bits_read = 0
        bit_position = start_bit
        integer_index = start_index
        
        while bits_read < num_bits:
            if integer_index >= len(compressed):
                # Si on n'a pas assez de données, on peut retourner ce qu'on a lu
                # mais cela indique une erreur dans les données
                break
            
            current_integer = compressed[integer_index]
            bit_offset = bit_position % 32
            bits_available = 32 - bit_offset
            bits_to_read_now = min(num_bits - bits_read, bits_available)
            
            extracted = self._extract_bits(current_integer, bit_offset, bits_to_read_now)
            value |= extracted << (num_bits - bits_read - bits_to_read_now)
            
            bits_read += bits_to_read_now
            bit_position += bits_to_read_now
            
            if bit_position % 32 == 0:
                integer_index += 1
        
        return value
    
    def _advance_position(self, bit_position: int, integer_index: int, 
                         num_bits: int) -> Tuple[int, int]:
        """Avance la position de num_bits."""
        new_bit_position = bit_position + num_bits
        new_integer_index = integer_index + (new_bit_position // 32)
        new_bit_position = new_bit_position % 32
        return new_bit_position, new_integer_index
    
    def get(self, i: int) -> int:
        """Obtient le i-ème entier du tableau compressé."""
        if i < 0 or i >= self.original_length or not self.compressed_data:
            raise IndexError(f"Index {i} hors limites [0, {self.original_length})")
        
        total_bits = 1 + max(self.value_bits, self.bits_for_overflow_index)
        
        if self.allow_consecutive:
            # Calculer la position du i-ème élément en parcourant les éléments précédents
            # Car les éléments peuvent avoir des tailles différentes
            bit_pos = 0
            int_idx = 0
            for j in range(i):
                # Lire le flag
                flag_temp = self._read_bits_consecutive(self.compressed_data, 1, bit_pos, int_idx)
                bit_pos, int_idx = self._advance_position(bit_pos, int_idx, 1)
                
                if flag_temp == 1:
                    # Overflow : avancer de bits_for_overflow_index
                    bit_pos, int_idx = self._advance_position(bit_pos, int_idx, self.bits_for_overflow_index)
                else:
                    # Régulier : avancer de value_bits
                    bit_pos, int_idx = self._advance_position(bit_pos, int_idx, self.value_bits)
            
            # Maintenant lire l'élément i
            flag = self._read_bits_consecutive(self.compressed_data, 1, bit_pos, int_idx)
            bit_pos, int_idx = self._advance_position(bit_pos, int_idx, 1)
            
            if flag == 1:
                overflow_idx = self._read_bits_consecutive(self.compressed_data,
                                                          self.bits_for_overflow_index,
                                                          bit_pos, int_idx)
                overflow_idx = overflow_idx & ((1 << self.bits_for_overflow_index) - 1)
                if overflow_idx < len(self.overflow_area):
                    return self.overflow_area[overflow_idx]
                return 0
            else:
                value = self._read_bits_consecutive(self.compressed_data, self.value_bits,
                                                   bit_pos, int_idx)
                value = value & ((1 << self.value_bits) - 1)
                if self.has_negative_numbers:
                    threshold = 1 << (self.value_bits - 1)
                    max_positive = threshold - 1
                    if value > max_positive:
                        value = -(value - threshold)
                return value
        else:
            # Mode non_consecutive : même logique que _decompress_non_consecutive
            # Parcourir les éléments précédents pour calculer la position de l'élément i
            bit_pos = 0
            int_idx = 0
            
            for j in range(i):
                pos_before = bit_pos
                idx_before = int_idx
                
                # Lire le flag pour connaître la taille de l'élément j
                flag_temp = self._read_bits_consecutive(self.compressed_data, 1, bit_pos, int_idx)
                
                if flag_temp == 1:
                    element_data_size = self.bits_for_overflow_index
                else:
                    element_data_size = self.value_bits
                
                element_total_size = 1 + element_data_size
                
                # Vérifier si l'élément j a été écrit dans un nouvel entier
                if pos_before + element_total_size > 32:
                    int_idx = idx_before + 1
                    bit_pos = element_total_size
                else:
                    bit_pos = pos_before + element_total_size
                    if bit_pos >= 32:
                        int_idx = idx_before + 1
                        bit_pos = 0
            
            # Lire l'élément i
            pos_before = bit_pos
            idx_before = int_idx
            
            # Lire le flag pour connaître la taille de l'élément i
            flag = self._read_bits_consecutive(self.compressed_data, 1, bit_pos, int_idx)
            
            if flag == 1:
                element_data_size = self.bits_for_overflow_index
            else:
                element_data_size = self.value_bits
            
            element_total_size = 1 + element_data_size
            
            # Vérifier si l'élément i a été écrit dans un nouvel entier
            if pos_before + element_total_size > 32:
                # Repositionner et relire depuis le prochain entier
                int_idx = idx_before + 1
                bit_pos = 0
                flag = self._read_bits_consecutive(self.compressed_data, 1, bit_pos, int_idx)
                bit_pos = 1
            else:
                # L'élément i est dans l'entier actuel
                bit_pos = pos_before + 1
            
            if flag == 1:
                overflow_idx = self._read_bits_consecutive(self.compressed_data,
                                                          self.bits_for_overflow_index,
                                                          bit_pos, int_idx)
                overflow_idx = overflow_idx & ((1 << self.bits_for_overflow_index) - 1)
                if overflow_idx < len(self.overflow_area):
                    return self.overflow_area[overflow_idx]
                return 0
            else:
                value = self._read_bits_consecutive(self.compressed_data, self.value_bits,
                                                   bit_pos, int_idx)
                value = value & ((1 << self.value_bits) - 1)
                if self.has_negative_numbers:
                    threshold = 1 << (self.value_bits - 1)
                    max_positive = threshold - 1
                    if value > max_positive:
                        value = -(value - threshold)
                return value

