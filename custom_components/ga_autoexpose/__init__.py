"""Google Assistant Auto-Expose Custom Integration."""
import os
import yaml
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.area_registry import async_get as async_get_area_registry
from homeassistant.helpers.event import async_call_later
from homeassistant.const import CLOUD_NEVER_EXPOSED_ENTITIES

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ga_autoexpose"
ASSISTANT = "cloud.google_assistant"
DEBOUNCE_TIME = 30  # Seconds to wait after a change before exporting


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Google Assistant Auto-Expose component."""

    # ------------------------------------------------------------------
    # CORE LOGIC: Export Function
    # ------------------------------------------------------------------
    async def export_google_assistant_entities(call=None):
        """Export Google Assistant exposed entities to a file."""
        _LOGGER.debug("Starting Google Assistant Auto-Expose export...")
        
        config_folder = os.path.dirname(hass.config.path("configuration.yaml"))
        output_file = os.path.join(config_folder, "exposed.yaml")

        try:
            # Access the exposed entities data manager
            exposed_entities = hass.data.get("homeassistant.exposed_entities")
            
            # Fetch all registers
            entity_registry = async_get_entity_registry(hass)
            device_registry = async_get_device_registry(hass)
            area_registry = async_get_area_registry(hass)

            if not exposed_entities:
                _LOGGER.error("Could not access exposed entities data.")
                return

            # Fetch settings
            assistant_settings = exposed_entities.async_get_assistant_settings(ASSISTANT)
            ga_config = hass.data.get("google_assistant", {})
            config_data = ga_config.get("config", {}) 
            expose_by_default = config_data.get("expose_by_default", False)
            exposed_domains = config_data.get("exposed_domains", [])
            
            exposed_entities_data = {}

            for entity_id, settings in assistant_settings.items():
                if entity_id in CLOUD_NEVER_EXPOSED_ENTITIES:
                    continue

                # --- STRICT FILTER LOGIC ---
                should_expose = settings.get("should_expose")
                include_entity = False

                if should_expose is True:
                    include_entity = True
                elif should_expose is False:
                    include_entity = False
                else:
                    if expose_by_default:
                        domain = entity_id.split(".")[0]
                        if domain in exposed_domains:
                            include_entity = True
                    else:
                        include_entity = False

                if not include_entity:
                    continue
                # ---------------------------

                # Get registry entry info
                registry_entry = entity_registry.async_get(entity_id)
                aliases = list(registry_entry.aliases) if registry_entry and registry_entry.aliases else []

                # Fetch names
                google_assistant_name = settings.get("name")
                friendly_name = getattr(registry_entry, "name", None)
                original_name = getattr(registry_entry, "original_name", None)
                
                # Device lookup
                device_entry = None
                if registry_entry and registry_entry.device_id:
                    device_entry = device_registry.async_get(registry_entry.device_id)

                # Determine device name fallback
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

                # Build data
                entity_data = {
                    "name": display_name,
                    "aliases": aliases,
                    "expose": True,
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
            
            # ------------------------------------------------------------------
            # NOTIFICATION LOGIC (Only if triggered by auto-updater, not manual service call)
            # We assume if call is None or comes from our internal scheduler, we notify.
            # ------------------------------------------------------------------
            if call is None or getattr(call, "context", None) is None: 
                message = (
                    "The device list for Google Assistant has been updated.\n\n"
                    "A restart is required to make the new devices visible.\n\n"
                    "[Click here to go to System Settings](/config/system)"
                )
                
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "Google Assistant Config Changed",
                        "message": message,
                        "notification_id": "ga_config_changed",
                    },
                )

        except Exception as e:
            _LOGGER.error(f"Error exporting entities: {e}", exc_info=True)


    # ------------------------------------------------------------------
    # AUTOMATION LOGIC: Event Listener & Debouncer
    # ------------------------------------------------------------------
    cancel_timer = None

    @callback
    def _schedule_export(event):
        """Schedule the export when entity registry changes."""
        # Only listen for updates or creates
        if event.data.get("action") not in ["create", "update"]:
            return

        nonlocal cancel_timer
        if cancel_timer:
            cancel_timer()
            cancel_timer = None

        # Helper function to run the async export from the sync callback
        async def _run_export_job(now):
            await export_google_assistant_entities()

        # Schedule execution after delay (Debounce)
        cancel_timer = async_call_later(hass, DEBOUNCE_TIME, _run_export_job)


    # Subscribe to Entity Registry Updates
    hass.bus.async_listen("entity_registry_updated", _schedule_export)
    
    # ------------------------------------------------------------------
    # REGISTER SERVICE
    # ------------------------------------------------------------------
    hass.services.async_register(DOMAIN, "export_entities", export_google_assistant_entities)
    
    return True
