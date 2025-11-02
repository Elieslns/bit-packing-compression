"""
Implémentation de la Compression BitPacking

Ce module implémente la compression de tableaux d'entiers en utilisant des techniques de bit packing.
Deux versions sont fournies :
1. BitPackingConsecutive : permet aux entiers compressés de s'étendre sur des entiers consécutifs
2. BitPackingNonConsecutive : les entiers compressés ne s'étendent jamais sur des entiers consécutifs
"""

import math
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional


class BitPackingBase(ABC):
    """Classe de base pour les algorithmes de compression bit packing."""
    
    def __init__(self):
        self.bits_per_element: int = 0
        self.compressed_data: List[int] = []
        self.original_length: int = 0
        self.has_negative_numbers: bool = False  # Indique si des nombres négatifs ont été encodés
    
    @abstractmethod
    def compress(self, array: List[int]) -> List[int]:
        """Compresse un tableau d'entiers."""
        pass
    
    @abstractmethod
    def decompress(self, compressed: List[int], result: List[int]) -> None:
        """Décompresse les données compressées dans le tableau résultat."""
        pass
    
    @abstractmethod
    def get(self, i: int) -> int:
        """Obtient le i-ème entier du tableau compressé sans décompression complète."""
        pass
    
    def _calculate_bits_needed(self, array: List[int]) -> int:
        """Calcule le nombre minimum de bits nécessaires pour représenter tous les entiers."""
        if not array:
            return 0
        
        has_negative = any(x < 0 for x in array)
        max_abs_value = max(abs(x) for x in array)
        
        if max_abs_value == 0:
            return 1
        
        if has_negative:
            # Avec l'encodage des négatifs (schéma d'offset), on peut représenter :
            # Plage : -(2^(k-1)-1) à 2^(k-1)-1 avec k bits
            # Donc on a besoin de k tel que max_abs_value <= 2^(k-1)-1
            # Cela signifie : 2^(k-1) >= max_abs_value + 1
            # k-1 >= log2(max_abs_value + 1)
            # k >= log2(max_abs_value + 1) + 1
            # Utiliser le plafond pour s'assurer d'avoir assez de bits
            bits = math.ceil(math.log2(max_abs_value + 1)) + 1
        else:
            # Sans négatifs, on peut représenter 0 à 2^k - 1
            # Donc on a besoin : 2^k > max_abs_value, i.e., k > log2(max_abs_value)
            # k = floor(log2(max_abs_value)) + 1
            bits = math.floor(math.log2(max_abs_value)) + 1
        
        return bits
    
    def _extract_bits(self, value: int, start_bit: int, num_bits: int) -> int:
        """Extrait num_bits bits de value en commençant à start_bit."""
        mask = ((1 << num_bits) - 1) << start_bit
        return (value & mask) >> start_bit
    
    def _set_bits(self, target: int, value: int, start_bit: int, num_bits: int) -> int:
        """Définit num_bits bits dans target en commençant à start_bit avec les num_bits bits de poids faible de value."""
        mask = ((1 << num_bits) - 1) << start_bit
        cleared = target & ~mask
        masked_value = (value & ((1 << num_bits) - 1)) << start_bit
        return cleared | masked_value


class BitPackingConsecutive(BitPackingBase):
    """
    Compression bit packing où les entiers compressés peuvent s'étendre sur 
    deux entiers consécutifs dans la sortie.
    """
    
    def compress(self, array: List[int]) -> List[int]:
        """
        Compresse un tableau d'entiers.
        Les entiers compressés peuvent s'étendre sur des entiers consécutifs en sortie.
        """
        if not array:
            return []
        
        self.original_length = len(array)
        self.has_negative_numbers = any(x < 0 for x in array)
        self.bits_per_element = self._calculate_bits_needed(array)
        
        compressed = []
        current_integer = 0
        current_bit_position = 0
        
        for value in array:
            bits_to_write = self.bits_per_element
            value_to_write = value
            
            # Gérer les nombres négatifs par offset (seulement si on a des négatifs)
            if self.has_negative_numbers and value < 0:
                value_to_write = (1 << (self.bits_per_element - 1)) + abs(value)
            
            while bits_to_write > 0:
                bits_available_in_current = 32 - current_bit_position
                bits_to_write_now = min(bits_to_write, bits_available_in_current)
                
                # Écrire les bits dans l'entier actuel
                current_integer = self._set_bits(
                    current_integer, 
                    value_to_write >> (bits_to_write - bits_to_write_now),
                    current_bit_position,
                    bits_to_write_now
                )
                
                current_bit_position += bits_to_write_now
                bits_to_write -= bits_to_write_now
                
                # Passer à l'entier suivant si l'actuel est plein
                if current_bit_position >= 32:
                    compressed.append(current_integer)
                    current_integer = 0
                    current_bit_position = 0
        
        # Ajouter le dernier entier s'il reste des données
        if current_bit_position > 0:
            compressed.append(current_integer)
        
        self.compressed_data = compressed
        return compressed
    
    def decompress(self, compressed: List[int], result: List[int]) -> None:
        """Décompresse les données compressées dans le tableau résultat."""
        if not compressed or self.original_length == 0:
            return
        
        result.clear()
        current_bit_position = 0
        current_integer_index = 0
        
        for _ in range(self.original_length):
            value = 0
            bits_read = 0
            bits_to_read = self.bits_per_element
            
            while bits_to_read > 0:
                if current_integer_index >= len(compressed):
                    break
                
                current_integer = compressed[current_integer_index]
                bits_available = 32 - current_bit_position
                bits_to_read_now = min(bits_to_read, bits_available)
                
                # Extraire les bits
                extracted = self._extract_bits(
                    current_integer,
                    current_bit_position,
                    bits_to_read_now
                )
                
                # Décaler à la position correcte dans la valeur finale
                shift_amount = self.bits_per_element - bits_read - bits_to_read_now
                value |= extracted << shift_amount
                bits_read += bits_to_read_now
                current_bit_position += bits_to_read_now
                bits_to_read -= bits_to_read_now
                
                # Passer à l'entier suivant si l'actuel est épuisé
                if current_bit_position >= 32:
                    current_integer_index += 1
                    current_bit_position = 0
            
            # Décoder les nombres négatifs (seulement si on a utilisé l'encodage négatif)
            if self.has_negative_numbers:
                # On utilise l'encodage par offset : les négatifs sont stockés comme offset + abs(valeur)
                # Seuil : 2^(bits_per_element - 1)
                # Valeurs < seuil : positives (0 à 2^(k-1)-1)
                # Valeurs >= seuil : négatives (encodées comme 2^(k-1) + abs(valeur))
                threshold = 1 << (self.bits_per_element - 1)
                max_positive = threshold - 1
                
                if value > max_positive:
                    # C'est un nombre négatif encodé avec offset
                    value = -(value - threshold)
            
            result.append(value)
        
        self.compressed_data = compressed
    
    def get(self, i: int) -> int:
        """Obtient le i-ème entier du tableau compressé sans décompression complète."""
        if i < 0 or i >= self.original_length or not self.compressed_data:
            raise IndexError(f"Index {i} hors limites [0, {self.original_length})")
        
        # Calculer la position bit du i-ème élément
        start_bit = i * self.bits_per_element
        
        value = 0
        bits_read = 0
        bits_to_read = self.bits_per_element
        
        current_bit_position = start_bit
        current_integer_index = current_bit_position // 32
        bit_offset = current_bit_position % 32
        
        while bits_to_read > 0:
            if current_integer_index >= len(self.compressed_data):
                break
            
            current_integer = self.compressed_data[current_integer_index]
            bits_available = 32 - bit_offset
            bits_to_read_now = min(bits_to_read, bits_available)
            
            # Extraire les bits
            extracted = self._extract_bits(current_integer, bit_offset, bits_to_read_now)
            
            # Décaler à la position correcte dans la valeur finale
            shift_amount = self.bits_per_element - bits_read - bits_to_read_now
            value |= extracted << shift_amount
            bits_read += bits_to_read_now
            bit_offset += bits_to_read_now
            bits_to_read -= bits_to_read_now
            
            # Passer à l'entier suivant si l'actuel est épuisé
            if bit_offset >= 32:
                current_integer_index += 1
                bit_offset = 0
        
        # Décoder les nombres négatifs (seulement si on a utilisé l'encodage négatif)
        if self.has_negative_numbers:
            threshold = 1 << (self.bits_per_element - 1)
            max_positive = threshold - 1
            if value > max_positive:
                value = -(value - threshold)
        
        return value


class BitPackingNonConsecutive(BitPackingBase):
    """
    Compression bit packing où les entiers compressés ne s'étendent jamais sur 
    deux entiers consécutifs dans la sortie.
    Chaque entier compressé tient dans un seul entier de sortie.
    """
    
    def compress(self, array: List[int]) -> List[int]:
        """
        Compresse un tableau d'entiers.
        Les entiers compressés ne s'étendent jamais sur des entiers consécutifs en sortie.
        """
        if not array:
            return []
        
        self.original_length = len(array)
        self.has_negative_numbers = any(x < 0 for x in array)
        self.bits_per_element = self._calculate_bits_needed(array)
        
        # Calculer combien d'éléments tiennent dans un entier 32 bits
        elements_per_integer = 32 // self.bits_per_element
        
        compressed = []
        current_integer = 0
        current_bit_position = 0
        elements_in_current = 0
        
        for value in array:
            # Gérer les nombres négatifs par offset (seulement si on a des négatifs)
            value_to_write = value
            if self.has_negative_numbers and value < 0:
                value_to_write = (1 << (self.bits_per_element - 1)) + abs(value)
            
            # Si l'entier actuel est plein, en commencer un nouveau
            if elements_in_current >= elements_per_integer:
                compressed.append(current_integer)
                current_integer = 0
                current_bit_position = 0
                elements_in_current = 0
            
            # Écrire la valeur dans l'entier actuel
            current_integer = self._set_bits(
                current_integer,
                value_to_write,
                current_bit_position,
                self.bits_per_element
            )
            
            current_bit_position += self.bits_per_element
            elements_in_current += 1
        
        # Ajouter le dernier entier s'il reste des données
        if elements_in_current > 0:
            compressed.append(current_integer)
        
        self.compressed_data = compressed
        return compressed
    
    def decompress(self, compressed: List[int], result: List[int]) -> None:
        """Décompresse les données compressées dans le tableau résultat."""
        if not compressed or self.original_length == 0:
            return
        
        result.clear()
        elements_per_integer = 32 // self.bits_per_element
        
        for compressed_int in compressed:
            current_bit_position = 0
            elements_read = 0
            
            while (elements_read < elements_per_integer and 
                   len(result) < self.original_length):
                # Extraire la valeur
                value = self._extract_bits(
                    compressed_int,
                    current_bit_position,
                    self.bits_per_element
                )
                
                # Décoder les nombres négatifs (seulement si on a utilisé l'encodage négatif)
                if self.has_negative_numbers:
                    threshold = 1 << (self.bits_per_element - 1)
                    max_positive = threshold - 1
                    if value > max_positive:
                        value = -(value - threshold)
                
                result.append(value)
                current_bit_position += self.bits_per_element
                elements_read += 1
        
        self.compressed_data = compressed
    
    def get(self, i: int) -> int:
        """Obtient le i-ème entier du tableau compressé sans décompression complète."""
        if i < 0 or i >= self.original_length or not self.compressed_data:
            raise IndexError(f"Index {i} hors limites [0, {self.original_length})")
        
        elements_per_integer = 32 // self.bits_per_element
        compressed_index = i // elements_per_integer
        element_offset = i % elements_per_integer
        
        if compressed_index >= len(self.compressed_data):
            raise IndexError(f"Index compressé {compressed_index} hors limites")
        
        compressed_int = self.compressed_data[compressed_index]
        bit_position = element_offset * self.bits_per_element
        
        value = self._extract_bits(compressed_int, bit_position, self.bits_per_element)
        
        # Décoder les nombres négatifs (seulement si on a utilisé l'encodage négatif)
        if self.has_negative_numbers:
            threshold = 1 << (self.bits_per_element - 1)
            max_positive = threshold - 1
            if value > max_positive:
                value = -(value - threshold)
        
        return value

