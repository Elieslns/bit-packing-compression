"""
Pattern Factory pour la Compression BitPacking

Ce module fournit une factory pour créer différents types de compresseurs bit packing
basés sur un seul paramètre.
"""

from enum import Enum
from typing import Optional
from bit_packing import BitPackingBase, BitPackingConsecutive, BitPackingNonConsecutive
from bit_packing_overflow import BitPackingOverflow


class CompressionType(Enum):
    """Énumération des types de compression disponibles."""
    CONSECUTIVE = "consecutive"
    NON_CONSECUTIVE = "non_consecutive"
    OVERFLOW_CONSECUTIVE = "overflow_consecutive"
    OVERFLOW_NON_CONSECUTIVE = "overflow_non_consecutive"


class BitPackingFactory:
    """Classe factory pour créer des compresseurs bit packing."""
    
    @staticmethod
    def create(compression_type: str, allow_consecutive: Optional[bool] = None) -> BitPackingBase:
        """
        Crée un compresseur bit packing basé sur une chaîne de type.
        
        Args:
            compression_type: Type de compression, un de :
                - "consecutive": Compression de base permettant l'extension
                - "non_consecutive": Compression de base sans extension
                - "overflow_consecutive": Compression avec débordement avec extension
                - "overflow_non_consecutive": Compression avec débordement sans extension
            allow_consecutive: Surcharge optionnelle pour les types overflow.
                            Si None, déterminé par compression_type.
        
        Returns:
            Instance BitPackingBase du type demandé.
        
        Raises:
            ValueError: Si compression_type n'est pas reconnu.
        """
        compression_type = compression_type.lower().strip()
        
        if compression_type == CompressionType.CONSECUTIVE.value:
            return BitPackingConsecutive()
        
        elif compression_type == CompressionType.NON_CONSECUTIVE.value:
            return BitPackingNonConsecutive()
        
        elif compression_type == CompressionType.OVERFLOW_CONSECUTIVE.value:
            return BitPackingOverflow(allow_consecutive=True)
        
        elif compression_type == CompressionType.OVERFLOW_NON_CONSECUTIVE.value:
            return BitPackingOverflow(allow_consecutive=False)
        
        else:
            raise ValueError(
                f"Unknown compression type: {compression_type}. "
                f"Available types: {[e.value for e in CompressionType]}"
            )
    
    @staticmethod
    def create_from_enum(compression_type: CompressionType) -> BitPackingBase:
        """
        Crée un compresseur bit packing à partir d'une énumération CompressionType.
        
        Args:
            compression_type: Valeur énumérée CompressionType.
        
        Returns:
            Instance BitPackingBase du type demandé.
        """
        return BitPackingFactory.create(compression_type.value)
    
    @staticmethod
    def list_available_types() -> list:
        """Retourne la liste des noms de types de compression disponibles."""
        return [e.value for e in CompressionType]

