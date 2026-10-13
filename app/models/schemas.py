from typing import Dict, List, Optional
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


class DietGoals(BaseModel):
    id: int = 1
    gender: str = Field("masculino", description="masculino | feminino")
    goal_type: str = Field("cutting", description="cutting | manutencao | bulking | personalizado")
    weight_kg: float = Field(78.0, ge=30.0, le=300.0)
    height_cm: float = Field(176.0, ge=100.0, le=250.0)
    age: int = Field(29, ge=12, le=110)
    activity_level: str = Field("moderado", description="sedentario | leve | moderado | intenso")
    daily_kcal_limit: float = Field(2000.0, gt=0.0)
    carbs_limit_g: float = Field(200.0, ge=0.0)
    proteins_limit_g: float = Field(150.0, ge=0.0)
    fat_limit_g: float = Field(65.0, ge=0.0)
    sodium_limit_mg: float = Field(2000.0, ge=0.0)


class DietGoalsUpdateRequest(BaseModel):
    gender: Optional[str] = "masculino"
    goal_type: str = "cutting"
    weight_kg: float = 78.0
    height_cm: float = 176.0
    age: int = 29
    activity_level: str = "moderado"
    auto_calculate: bool = False
    daily_kcal_limit: Optional[float] = None
    carbs_limit_g: Optional[float] = None
    proteins_limit_g: Optional[float] = None
    fat_limit_g: Optional[float] = None
    sodium_limit_mg: Optional[float] = None


class DietDiaryEntry(BaseModel):
    id: int
    date_str: str
    meal_type: str
    product_name: str
    source_type: str
    portion_g: float
    kcal: float
    carbohydrates_g: float
    proteins_g: float
    fat_g: float
    fiber_g: float
    sodium_mg: float
    calcium_mg: float = 0.0
    iron_mg: float = 0.0
    potassium_mg: float = 0.0
    magnesium_mg: float = 0.0
    phosphorus_mg: float = 0.0
    vitamin_c_mg: float = 0.0
    zinc_mg: float = 0.0
    created_at: str


class DietDiaryCreateRequest(BaseModel):
    date_str: Optional[str] = None
    meal_type: str = Field("Lanche", description="Café da manhã | Almoço | Lanche | Jantar")
    product_name: str
    source_type: str = Field("foto_ficha", description="foto_ficha | codigo_barras | manual")
    portion_g: float = Field(100.0, gt=0.0)
    kcal: float = Field(0.0, ge=0.0)
    carbohydrates_g: float = Field(0.0, ge=0.0)
    proteins_g: float = Field(0.0, ge=0.0)
    fat_g: float = Field(0.0, ge=0.0)
    fiber_g: float = Field(0.0, ge=0.0)
    sodium_mg: float = Field(0.0, ge=0.0)
    calcium_mg: float = Field(0.0, ge=0.0)
    iron_mg: float = Field(0.0, ge=0.0)
    potassium_mg: float = 0.0
    magnesium_mg: float = 0.0
    phosphorus_mg: float = 0.0
    vitamin_c_mg: float = 0.0
    zinc_mg: float = 0.0


class DietTodaySummary(BaseModel):
    date_str: str
    goals: DietGoals
    consumed: Dict[str, float]
    remaining: Dict[str, float]
    percentages: Dict[str, float]
    status_label: str
    within_kcal_limit: bool
    entries: List[DietDiaryEntry]


class LabelParseResult(BaseModel):
    product_name: str
    brand: str = "Ficha técnica escaneada"
    sample_id: Optional[str] = None
    image_url: Optional[str] = None
    ocr_engine: str = "nutriscan_regex_br"
    raw_ocr_text: str
    portion_label_g: float
    portion_consumed_g: float
    scale_factor: float
    per_label_portion: Dict[str, float]
    per_100g: NutritionPer100g
    consumed_macros: Dict[str, float]
    daily_limit_impact_pct: Dict[str, float]
    anvisa: AnvisaAlerts
    nutriscore_grade: str


class WaterLogCreate(BaseModel):
    amount_ml: int
    date_str: Optional[str] = None


class WaterLogResponse(BaseModel):
    id: int
    date_str: str
    amount_ml: int
    goal_ml: int
    remaining_ml: int
    pct: float


class DailyTrendItem(BaseModel):
    date_str: str
    weekday_short: str
    total_kcal: float
    kcal_limit: float
    pct_kcal: float
    total_prot: float
    total_carbs: float
    total_fat: float
    total_water_ml: int
    met_goal: bool


class WeeklyTrendsResponse(BaseModel):
    days: List[DailyTrendItem]
    avg_kcal: float
    compliance_rate: float
    total_water_liters: float


class MicronutrientTotals(BaseModel):
    calcium_mg: float = Field(0.0, description="Cálcio em miligramas")
    iron_mg: float = Field(0.0, description="Ferro em miligramas")
    sodium_mg: float = Field(0.0, description="Sódio em miligramas")
    potassium_mg: float = Field(0.0, description="Potássio em miligramas")
    magnesium_mg: float = Field(0.0, description="Magnésio em miligramas")
    phosphorus_mg: float = Field(0.0, description="Fósforo em miligramas")
    vitamin_c_mg: float = Field(0.0, description="Vitamina C em miligramas")
    zinc_mg: float = Field(0.0, description="Zinco em miligramas")


class MicronutrientIDRComparison(BaseModel):
    nutrient: str = Field(..., description="Nome do nutriente")
    unit: str = Field("mg", description="Unidade de medida")
    consumed: float = Field(..., description="Quantidade total consumida")
    idr_goal: float = Field(..., description="Meta ou limite de IDR ANVISA")
    pct_idr: float = Field(..., description="Percentual atingido em relação à IDR")
    status: str = Field(..., description="Status de adequação: Excelente | Adequado | Abaixo da meta | Atenção: Alto")


class DailyMicronutrientsResponse(BaseModel):
    date_str: str
    totals: MicronutrientTotals
    comparisons: List[MicronutrientIDRComparison]




class PlateItemDetail(BaseModel):
    food_key: str
    food_name: str
    category: str
    weight_g: float
    kcal: float
    carbohydrates_g: float
    proteins_g: float
    fat_g: float
    fiber_g: float
    calcium_mg: float = 0.0
    iron_mg: float = 0.0
    sodium_mg: float = 0.0
    potassium_mg: float = 0.0
    vitamin_c_mg: float = 0.0
    magnesium_mg: float = 0.0
    zinc_mg: float = 0.0


class PlateAnalysisTotals(BaseModel):
    kcal: float
    carbohydrates_g: float
    proteins_g: float
    fat_g: float
    fiber_g: float


class PlateMicronutrients(BaseModel):
    calcium_mg: float
    iron_mg: float
    sodium_mg: float
    potassium_mg: float
    vitamin_c_mg: float
    magnesium_mg: float
    zinc_mg: float


class PlateAnalysisResponse(BaseModel):
    plate_name: str
    confidence: float
    total_weight_g: float
    plate_diameter_cm: float = 25.0
    sample_id: Optional[str] = None
    description: Optional[str] = None
    items: List[PlateItemDetail]
    totals: PlateAnalysisTotals
    micronutrients: PlateMicronutrients
    daily_goal_impact_pct: Dict[str, float]
    anvisa_idr_impact_pct: Dict[str, float]
    heuristic_clusters: Optional[Dict[str, int]] = None