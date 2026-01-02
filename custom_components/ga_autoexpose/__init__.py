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
            # Access the exposed entities data manager
            exposed_entities = hass.data.get("homeassistant.exposed_entities")
            
            # Fetch all registries (Entity, Device, and Area)
            entity_registry = async_get_entity_registry(hass)
            device_registry = async_get_device_registry(hass)
            area_registry = async_get_area_registry(hass)

            if not exposed_entities:
                _LOGGER.error("Could not access exposed entities data.")
                return

            # Fetch settings and configuration
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

                # --- STRICT FILTER LOGIC ---
                should_expose = settings.get("should_expose")
                
                # Flag to determine if this entity should be included
                include_entity = False

                if should_expose is True:
                    # 1. User explicitly enabled 'Expose' in the UI
                    include_entity = True
                elif should_expose is False:
                    # 2. User explicitly enabled 'Don't Expose'
                    include_entity = False
                else:
                    # 3. should_expose is None (No specific choice made in UI)
                    if expose_by_default:
                        # Only check domain if global default is True
                        domain = entity_id.split(".")[0]
                        if domain in exposed_domains:
                            include_entity = True
                    else:
                        # If global default is False, and UI is not explicitly True -> Skip
                        include_entity = False

                # If it doesn't pass the filter, skip to the next entity
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
                
                # Device lookup (for name and area)
                device_entry = None
                if registry_entry and registry_entry.device_id:
                    device_entry = device_registry.async_get(registry_entry.device_id)

                # Determine device name as fallback
                device_name = None
                if not friendly_name and not original_name and not google_assistant_name and device_entry:
                    device_name = getattr(device_entry, "name_by_user", None) or getattr(device_entry, "name", None)

                # Determine display name
                display_name = friendly_name or google_assistant_name or original_name or device_name or entity_id

                # Room (Area) Logic
                room_name = None
                if registry_entry:
                    area_id = registry_entry.area_id
                    
                    # If entity has no area, use the device area
                    if not area_id and device_entry:
                        area_id = device_entry.area_id
                    
                    # Fetch name by ID
                    if area_id:
                        area = area_registry.async_get_area(area_id)
                        if area:
                            room_name = area.name

                # Construct the data
                entity_data = {
                    "name": display_name,
                    "aliases": aliases,
                    "expose": True,  # Force expose: true for the YAML
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
