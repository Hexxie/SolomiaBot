@startuml
!theme plain

entity "food_categories" as FC {
    * id : int <<PK>>
    --
    name : string
    examples : text[]
    embedding : vector(1536)
}

entity "food_slots" as FS {
    * id : int <<PK>>
    --
    code : string(2)
    description : string
    allowed_categories : int[]  // references FC.id
}

entity "meal_templates" as MT {
    * id : int <<PK>>
    --
    name : string
    order : int
    slot_codes : string[]
}

entity "user_meal_log" as ML {
    * id : int <<PK>>
    --
    user_id : int
    date : date
    meal_id : int <<FK to MT.id>>
    slot_code : string(2) <<FK to FS.code>>
    product_name : string
    grams : float
    portion_fraction : float
}

FC ||--o{ FS : "allowed_categories"
FS ||--o{ MT : "slot_codes"
MT ||--o{ ML : "meals"
FS ||--o{ ML : "slots"
@enduml
