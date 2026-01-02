"""Google Assistant Auto-Expose Custom Integration."""
import os
import yaml
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ga_autoexpose"
ASSISTANT = "cloud.google_assistant"


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Google Assistant Auto-Expose component."""
    
    async def export_google_assistant_entities(call):
        """Export Google Assistant exposed entities to a file."""
        config_folder = os.path.dirname(hass.config.path("configuration.yaml"))
        output_file = os.path.join(config_folder, "exposed.yaml")

        try:
            # Toegang tot de exposed entities data manager
            exposed_entities = hass.data.get("homeassistant.exposed_entities")
            
            # Haal alle registers op (Entity, Device en Area)
            entity_registry = async_get_entity_registry(hass)
            device_registry = async_get_device_registry(hass)
            area_registry = async_get_area_registry(hass)

            if not exposed_entities:
                _LOGGER.error("Could not access exposed entities data.")
                return

            # Instellingen ophalen
            assistant_settings = exposed_entities.async_get_assistant_settings(ASSISTANT)
            ga_config = hass.data.get("google_assistant", {})
            config_data = ga_config.get("config", {}) 
            expose_by_default = config_data.get("expose_by_default", False)
            exposed_domains = config_data.get("exposed_domains", [])
            
            _LOGGER.debug("Start export. expose_by_default: %s", expose_by_default)

            exposed_entities_data = {}

            for entity_id, settings in assistant_settings.items():
                if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
                    continue

                # --- HIER IS DE STRENGE FILTER LOGICA ---
                should_expose = settings.get("should_expose")
                
                # Variabele om te bepalen of we deze entiteit opnemen
                include_entity = False

                if should_expose is True:
                    # 1. Gebruiker heeft expliciet 'Expose' aangezet in de UI
                    include_entity = True
                elif should_expose is False:
                    # 2. Gebruiker heeft expliciet 'Don't Expose' aangezet
                    include_entity = False
                else:
                    # 3. should_expose is None (Geen specifieke keuze gemaakt in UI)
                    if expose_by_default:
                        # Alleen als global default op True staat, checken we het domein
                        domain = entity_id.split(".")[0]
                        if domain in exposed_domains:
                            include_entity = True
                    else:
                        # Als global default False is (jouw situatie), en UI is niet expliciet True -> Skippen
                        include_entity = False

                # Als hij niet door de filter komt, ga direct naar de volgende
                if not include_entity:
                    continue
                # ----------------------------------------

                # Get registry entry info
                registry_entry = entity_registry.async_get(entity_id)
                aliases = list(registry_entry.aliases) if registry_entry and registry_entry.aliases else []

                # Fetch names
                google_assistant_name = settings.get("name")
                friendly_name = getattr(registry_entry, "name", None)
                original_name = getattr(registry_entry, "original_name", None)
                
                # Device lookup (voor naam en area)
                device_entry = None
                if registry_entry and registry_entry.device_id:
                    device_entry = device_registry.async_get(registry_entry.device_id)

                # Bepaal device naam als fallback
                device_name = None
                if not friendly_name and not original_name and not google_assistant_name and device_entry:
                    device_name = getattr(device_entry, "name_by_user", None) or getattr(device_entry, "name", None)

                # Determine display name
                display_name = friendly_name or google_assistant_name or original_name or device_name or entity_id

                # Room (Area) Logic
                room_name = None
                if registry_entry:
                    area_id = registry_entry.area_id
                    
                    if not area_id and device_entry:
                        area_id = device_entry.area_id
                    
                    if area_id:
                        area = area_registry.async_get_area(area_id)
                        if area:
                            room_name = area.name

                # Bouw de data op
                entity_data = {
                    "name": display_name,
                    "aliases": aliases,
                    "expose": True,  # Forceer expose true voor de YAML
                }

                if room_name:
                    entity_data["room"] = room_name

                exposed_entities_data[entity_id] = entity_data

            # Write to file
            def write_to_file():
                with open(output_file, "w", encoding="utf-8") as file:
                    yaml.dump(
                        exposed_entities_data,
                        file,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

            await hass.async_add_executor_job(write_to_file)
            _LOGGER.info(f"Exported {len(exposed_entities_data)} entities to {output_file}")

        except Exception as e:
            _LOGGER.error(f"Error exporting entities: {e}", exc_info=True)

    # Register the service
    hass.services.async_register(DOMAIN, "export_entities", export_google_assistant_entities)
    return True
