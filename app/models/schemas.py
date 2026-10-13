from typing import List, Optional
from pydantic import BaseModel, Field


class NutritionPer100g(BaseModel):
    energy_kcal: float = Field(0.0, description="Energia em kcal por 100g ou 100ml")
    carbohydrates_g: float = Field(0.0, description="Carboidratos em gramas por 100g/ml")
    sugars_g: float = Field(0.0, description="Açúcares totais em gramas por 100g/ml")
    fat_g: float = Field(0.0, description="Gorduras totais em gramas por 100g/ml")
    saturated_fat_g: float = Field(0.0, description="Gorduras saturadas em gramas por 100g/ml")
    proteins_g: float = Field(0.0, description="Proteínas em gramas por 100g/ml")
    fiber_g: float = Field(0.0, description="Fibras alimentares em gramas por 100g/ml")
    sodium_mg: float = Field(0.0, description="Sódio em miligramas por 100g/ml")
    salt_g: float = Field(0.0, description="Sal equivalente em gramas por 100g/ml")


class AnvisaAlerts(BaseModel):
    is_beverage: bool = Field(False, description="Indica se aplica limites líquidos (por 100ml)")
    high_sugar: bool = Field(False, description="Acima do limite ANVISA RDC 429/2020 para açúcares")
    high_saturated_fat: bool = Field(False, description="Acima do limite ANVISA RDC 429/2020 para gordura saturada")
    high_sodium: bool = Field(False, description="Acima do limite ANVISA RDC 429/2020 para sódio")
    warnings_count: int = Field(0, description="Quantidade total de lupas frontais ANVISA")
    warnings_list: List[str] = Field(default_factory=list, description="Rótulos de alerta frontal ANVISA")
    thresholds_used: dict = Field(default_factory=dict, description="Limites de corte aplicados na avaliação")


class AdditiveItem(BaseModel):
    code: str = Field(..., description="Código INS / número E do aditivo (ex: E322)")
    name: str = Field(..., description="Nome em português do aditivo")
    function: str = Field(..., description="Classe funcional tecnológica (ex: emulsificante, conservante)")


class ProductAnalysis(BaseModel):
    barcode: str
    product_name: str
    brand: str
    quantity: str = "100g"
    categories: str = ""
    is_beverage: bool = False
    nutriscore_grade: str = Field("C", description="Letra de A a E")
    nova_group: int = Field(3, description="Grupo NOVA de 1 a 4")
    nova_label: str = Field("", description="Classificação de processamento segundo guia da USP")
    ingredients_text: str = ""
    allergens: List[str] = Field(default_factory=list)
    additives: List[AdditiveItem] = Field(default_factory=list)
    nutrition: NutritionPer100g
    anvisa: AnvisaAlerts
    source: str = "openfoodfacts"
    scanned_at: Optional[str] = None


class NutrientDelta(BaseModel):
    metric: str
    label: str
    unit: str
    value_a: float
    value_b: float
    diff: float
    lower_is_better: bool = True
    favorable_barcode: Optional[str] = None


class ComparisonResponse(BaseModel):
    product_a: ProductAnalysis
    product_b: ProductAnalysis
    deltas: List[NutrientDelta]
    summary_notes: List[str]
