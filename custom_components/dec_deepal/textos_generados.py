"""Textos de los avisos y del catálogo, por idioma.

FICHERO GENERADO: no editar. Los textos están en ``idiomas/<idioma>.json``;
tras cambiarlos, ejecutar ``python tools/generar_idiomas.py``.
"""

from __future__ import annotations

from typing import Final

#: Idioma que se usa cuando el del usuario no está traducido.
BASE_LANGUAGE: Final = "en"
#: Idiomas sin traducción propia que usan la de otro.
BORROWED_LANGUAGES: Final[dict[str, str]] = {
    "ca": "es",
    "eu": "es",
    "gl": "es"
}
#: Mensajes de los avisos al móvil: ``{idioma: {clave: texto}}``.
ALERT_TEXTS: Final[dict[str, dict[str, str]]] = {
    "es": {
        "charge_started": "Carga iniciada{battery}.",
        "charge_interrupted": "Carga interrumpida{battery}.",
        "charge_finished": "Carga terminada{battery}.",
        "battery": " (batería al {level} %)",
        "warnings": "Testigo encendido: {names}.",
        "tires": "Aviso de neumáticos: {names}.",
        "key_battery": "Pila del mando baja. Cámbiala por una CR2032.",
        "maintenance_remaining": "Quedan {parts} para la {ordinal} revisión.",
        "maintenance_overdue": "Mantenimiento vencido: la {ordinal} revisión tocaba el {date} o a los {km} km.",
        "itv_remaining": "Quedan {days} para la ITV (límite: {date}).",
        "itv_today": "Hoy es el último día para pasar la ITV.",
        "itv_overdue": "ITV vencida desde el {date}.",
        "insurance_cancel": "Seguro: quedan {days} para poder desistir (hasta el {deadline}). Renueva el {renewal}.",
        "insurance_last_day": "Seguro: hoy es el último día para avisar a {company} si no quieres renovar.",
        "insurance_renewed": "Seguro renovado hoy. Próxima renovación: {renewal}.",
        "your_insurer": "tu aseguradora",
        "km": "{value} km",
        "days": "{value} días",
        "day": "1 día",
        "or": " o ",
        "and": " y ",
        "thousands": ".",
        "ordinal": "{number}ª",
        "date_format": "%d/%m/%Y"
    },
    "en": {
        "charge_started": "Charging started{battery}.",
        "charge_interrupted": "Charging interrupted{battery}.",
        "charge_finished": "Charging finished{battery}.",
        "battery": " (battery at {level}%)",
        "warnings": "Warning light on: {names}.",
        "tires": "Tyre warning: {names}.",
        "key_battery": "Key fob battery low. Replace it with a CR2032.",
        "maintenance_remaining": "{parts} left until the {ordinal} service.",
        "maintenance_overdue": "Service overdue: the {ordinal} service was due on {date} or at {km} km.",
        "itv_remaining": "{days} left until the roadworthiness test (ITV), due by {date}.",
        "itv_today": "Today is the last day to pass the roadworthiness test (ITV).",
        "itv_overdue": "Roadworthiness test (ITV) overdue since {date}.",
        "insurance_cancel": "Insurance: {days} left to cancel (until {deadline}). It renews on {renewal}.",
        "insurance_last_day": "Insurance: today is the last day to tell {company} that you do not want to renew.",
        "insurance_renewed": "Insurance renewed today. Next renewal: {renewal}.",
        "your_insurer": "your insurer",
        "km": "{value} km",
        "days": "{value} days",
        "day": "1 day",
        "or": " or ",
        "and": " and ",
        "thousands": ",",
        "ordinal": "{number}",
        "date_format": "%d/%m/%Y"
    },
    "pt": {
        "charge_started": "Carregamento iniciado{battery}.",
        "charge_interrupted": "Carregamento interrompido{battery}.",
        "charge_finished": "Carregamento terminado{battery}.",
        "battery": " (bateria a {level} %)",
        "warnings": "Luz de aviso acesa: {names}.",
        "tires": "Aviso dos pneus: {names}.",
        "key_battery": "Pilha da chave fraca. Substitua-a por uma CR2032.",
        "maintenance_remaining": "Faltam {parts} para a {ordinal} revisão.",
        "maintenance_overdue": "Manutenção vencida: a {ordinal} revisão devia ter sido feita a {date} ou aos {km} km.",
        "itv_remaining": "Faltam {days} para a ITV (limite: {date}).",
        "itv_today": "Hoje é o último dia para fazer a ITV.",
        "itv_overdue": "ITV vencida desde {date}.",
        "insurance_cancel": "Seguro: faltam {days} para poder cancelar (até {deadline}). Renova a {renewal}.",
        "insurance_last_day": "Seguro: hoje é o último dia para avisar {company} se não quiser renovar.",
        "insurance_renewed": "Seguro renovado hoje. Próxima renovação: {renewal}.",
        "your_insurer": "a sua seguradora",
        "km": "{value} km",
        "days": "{value} dias",
        "day": "1 dia",
        "or": " ou ",
        "and": " e ",
        "thousands": ".",
        "ordinal": "{number}.ª",
        "date_format": "%d/%m/%Y"
    },
    "it": {
        "charge_started": "Ricarica avviata{battery}.",
        "charge_interrupted": "Ricarica interrotta{battery}.",
        "charge_finished": "Ricarica terminata{battery}.",
        "battery": " (batteria al {level} %)",
        "warnings": "Spia accesa: {names}.",
        "tires": "Avviso pneumatici: {names}.",
        "key_battery": "Batteria della chiave scarica. Sostituiscila con una CR2032.",
        "maintenance_remaining": "Mancano {parts} al {ordinal} tagliando.",
        "maintenance_overdue": "Manutenzione scaduta: il {ordinal} tagliando era previsto per il {date} o a {km} km.",
        "itv_remaining": "Mancano {days} all'ITV (limite: {date}).",
        "itv_today": "Oggi è l'ultimo giorno per fare l'ITV.",
        "itv_overdue": "ITV scaduta dal {date}.",
        "insurance_cancel": "Assicurazione: mancano {days} per poter disdire (fino al {deadline}). Si rinnova il {renewal}.",
        "insurance_last_day": "Assicurazione: oggi è l'ultimo giorno per avvisare {company} se non vuoi rinnovare.",
        "insurance_renewed": "Assicurazione rinnovata oggi. Prossimo rinnovo: {renewal}.",
        "your_insurer": "la tua compagnia",
        "km": "{value} km",
        "days": "{value} giorni",
        "day": "1 giorno",
        "or": " o ",
        "and": " e ",
        "thousands": ".",
        "ordinal": "{number}º",
        "date_format": "%d/%m/%Y"
    },
    "pl": {
        "charge_started": "Rozpoczęto ładowanie{battery}.",
        "charge_interrupted": "Przerwano ładowanie{battery}.",
        "charge_finished": "Zakończono ładowanie{battery}.",
        "battery": " (akumulator: {level} %)",
        "warnings": "Zapaliła się kontrolka: {names}.",
        "tires": "Ostrzeżenie o oponach: {names}.",
        "key_battery": "Słaba bateria kluczyka. Wymień ją na CR2032.",
        "maintenance_remaining": "Do {ordinal} przeglądu: {parts}.",
        "maintenance_overdue": "Serwis po terminie: {ordinal} przegląd przypadał {date} lub przy {km} km.",
        "itv_remaining": "Do ITV: {days} (termin: {date}).",
        "itv_today": "Dziś jest ostatni dzień na wykonanie ITV.",
        "itv_overdue": "ITV po terminie od {date}.",
        "insurance_cancel": "Ubezpieczenie: na wypowiedzenie zostało {days} (do {deadline}). Odnowienie: {renewal}.",
        "insurance_last_day": "Ubezpieczenie: dziś ostatni dzień, aby powiadomić ({company}), jeśli nie chcesz przedłużać.",
        "insurance_renewed": "Ubezpieczenie odnowione dzisiaj. Następne odnowienie: {renewal}.",
        "your_insurer": "Twój ubezpieczyciel",
        "km": "{value} km",
        "days": "{value} dni",
        "day": "1 dzień",
        "or": " lub ",
        "and": " i ",
        "thousands": " ",
        "ordinal": "{number}.",
        "date_format": "%d.%m.%Y"
    }
}
#: Nombres del catálogo: ``{idioma: {clave: texto}}``.
CATALOGUE_TEXTS: Final[dict[str, dict[str, str]]] = {
    "es": {
        "operacion_general_inspection": "Inspección general (propulsión, batería, alta tensión, frenos y dirección)",
        "operacion_tyres": "Neumáticos (inspección y ajuste)",
        "operacion_cabin_filter": "Filtro del aire acondicionado (revisar o cambiar)",
        "operacion_condenser_cleaning": "Limpieza del condensador y del evaporador",
        "operacion_electrics_inspection": "Inspección de electricidad, aire acondicionado y mangueras de refrigeración",
        "operacion_brake_fluid": "Cambio del líquido de frenos (cada 2 años o 40.000 km)",
        "operacion_coolant": "Cambio del líquido refrigerante (cada 3 años u 80.000 km)",
        "operacion_front_gear_oil": "Cambio del aceite del reductor delantero (cada 3 años o 60.000 km)",
        "operacion_rear_gear_oil": "Cambio del aceite del reductor trasero (cada 5 años o 100.000 km)"
    },
    "en": {
        "operacion_general_inspection": "General inspection (drive unit, battery, high voltage, brakes and steering)",
        "operacion_tyres": "Tyres (inspection and adjustment)",
        "operacion_cabin_filter": "Cabin air filter (check or replace)",
        "operacion_condenser_cleaning": "Condenser and evaporator cleaning",
        "operacion_electrics_inspection": "Inspection of electrics, air conditioning and coolant hoses",
        "operacion_brake_fluid": "Brake fluid change (every 2 years or 40,000 km)",
        "operacion_coolant": "Coolant change (every 3 years or 80,000 km)",
        "operacion_front_gear_oil": "Front reduction gear oil change (every 3 years or 60,000 km)",
        "operacion_rear_gear_oil": "Rear reduction gear oil change (every 5 years or 100,000 km)"
    },
    "pt": {
        "operacion_general_inspection": "Inspeção geral (propulsão, bateria, alta tensão, travões e direção)",
        "operacion_tyres": "Pneus (inspeção e ajuste)",
        "operacion_cabin_filter": "Filtro do ar condicionado (verificar ou substituir)",
        "operacion_condenser_cleaning": "Limpeza do condensador e do evaporador",
        "operacion_electrics_inspection": "Inspeção da parte elétrica, do ar condicionado e das mangueiras de refrigeração",
        "operacion_brake_fluid": "Substituição do líquido dos travões (a cada 2 anos ou 40.000 km)",
        "operacion_coolant": "Substituição do líquido de refrigeração (a cada 3 anos ou 80.000 km)",
        "operacion_front_gear_oil": "Substituição do óleo do redutor dianteiro (a cada 3 anos ou 60.000 km)",
        "operacion_rear_gear_oil": "Substituição do óleo do redutor traseiro (a cada 5 anos ou 100.000 km)"
    },
    "it": {
        "operacion_general_inspection": "Ispezione generale (propulsione, batteria, alta tensione, freni e sterzo)",
        "operacion_tyres": "Pneumatici (ispezione e regolazione)",
        "operacion_cabin_filter": "Filtro dell'aria condizionata (controllare o sostituire)",
        "operacion_condenser_cleaning": "Pulizia del condensatore e dell'evaporatore",
        "operacion_electrics_inspection": "Ispezione di impianto elettrico, aria condizionata e tubi di raffreddamento",
        "operacion_brake_fluid": "Sostituzione del liquido dei freni (ogni 2 anni o 40.000 km)",
        "operacion_coolant": "Sostituzione del liquido di raffreddamento (ogni 3 anni o 80.000 km)",
        "operacion_front_gear_oil": "Sostituzione dell'olio del riduttore anteriore (ogni 3 anni o 60.000 km)",
        "operacion_rear_gear_oil": "Sostituzione dell'olio del riduttore posteriore (ogni 5 anni o 100.000 km)"
    },
    "pl": {
        "operacion_general_inspection": "Przegląd ogólny (napęd, akumulator, wysokie napięcie, hamulce i układ kierowniczy)",
        "operacion_tyres": "Opony (kontrola i regulacja)",
        "operacion_cabin_filter": "Filtr kabinowy (sprawdzić lub wymienić)",
        "operacion_condenser_cleaning": "Czyszczenie skraplacza i parownika",
        "operacion_electrics_inspection": "Kontrola instalacji elektrycznej, klimatyzacji i przewodów chłodzenia",
        "operacion_brake_fluid": "Wymiana płynu hamulcowego (co 2 lata lub 40 000 km)",
        "operacion_coolant": "Wymiana płynu chłodzącego (co 3 lata lub 80 000 km)",
        "operacion_front_gear_oil": "Wymiana oleju przedniej przekładni redukcyjnej (co 3 lata lub 60 000 km)",
        "operacion_rear_gear_oil": "Wymiana oleju tylnej przekładni redukcyjnej (co 5 lat lub 100 000 km)"
    }
}
