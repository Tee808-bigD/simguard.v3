"""Nokia CAMARA API integration — SIM Swap & Device Swap via Network as Code SDK.

Uses Nokia test numbers for sandbox mode:
  +99999991000  → SIM swap occurred
  +99999991001  → No SIM swap
  +99999991002  → Device swap occurred
"""

import logging
from datetime import datetime
from typing import Optional
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CamaraService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-init the Nokia SDK client."""
        if self._client is None:
            if not settings.nac_api_key:
                logger.warning("NAC_API_KEY not set — CAMARA calls will use simulation mode")
                return None
            try:
                import network_as_code as nac
                self._client = nac.NetworkAsCodeClient(token=settings.nac_api_key)
            except Exception as e:
                logger.error(f"Failed to init Nokia SDK: {e}")
                return None
        return self._client

    def check_sim_swap(self, phone_number: str, max_age_hours: int = 240) -> dict:
        """Check if a SIM swap occurred within max_age_hours.

        Returns:
            {
                "swapped": bool,
                "swap_date": str | None,
                "max_age_hours": int,
                "source": "camara" | "simulation"
            }
        """
        client = self._get_client()
        if client is None:
            return self._simulate_sim_swap(phone_number, max_age_hours)

        try:
            device = client.devices.get(phone_number=phone_number)
            result = device.sim_swap.verify(max_age=max_age_hours)
            swap_date = None
            try:
                swap_date_obj = device.sim_swap.retrieve_date()
                swap_date = swap_date_obj.isoformat() if swap_date_obj else None
            except Exception:
                pass

            return {
                "swapped": bool(result),
                "swap_date": swap_date,
                "max_age_hours": max_age_hours,
                "source": "camara"
            }
        except Exception as e:
            logger.error(f"SIM swap check failed for {phone_number}: {e}")
            return self._simulate_sim_swap(phone_number, max_age_hours)

    def check_device_swap(self, phone_number: str, max_age_hours: int = 240) -> dict:
        """Check if a device swap occurred within max_age_hours."""
        client = self._get_client()
        if client is None:
            return self._simulate_device_swap(phone_number, max_age_hours)

        try:
            device = client.devices.get(phone_number=phone_number)
            result = device.device_swap.verify(max_age=max_age_hours)
            swap_date = None
            try:
                swap_date_obj = device.device_swap.retrieve_date()
                swap_date = swap_date_obj.isoformat() if swap_date_obj else None
            except Exception:
                pass

            return {
                "swapped": bool(result),
                "swap_date": swap_date,
                "max_age_hours": max_age_hours,
                "source": "camara"
            }
        except Exception as e:
            logger.error(f"Device swap check failed for {phone_number}: {e}")
            return self._simulate_device_swap(phone_number, max_age_hours)

    def _simulate_sim_swap(self, phone_number: str, max_age_hours: int) -> dict:
        """Deterministic simulation using Nokia test numbers."""
        # Nokia sandbox test numbers
        swapped = phone_number in ("+99999991000",)
        return {
            "swapped": swapped,
            "swap_date": "2026-04-10T08:30:00Z" if swapped else None,
            "max_age_hours": max_age_hours,
            "source": "simulation"
        }

    def _simulate_device_swap(self, phone_number: str, max_age_hours: int) -> dict:
        swapped = phone_number in ("+99999991002",)
        return {
            "swapped": swapped,
            "swap_date": "2026-04-12T14:00:00Z" if swapped else None,
            "max_age_hours": max_age_hours,
            "source": "simulation"
        }

    def full_check(self, phone_number: str) -> dict:
        """Run all CAMARA checks for a phone number."""
        sim = self.check_sim_swap(phone_number, max_age_hours=24)
        sim_7d = self.check_sim_swap(phone_number, max_age_hours=168)
        device = self.check_device_swap(phone_number, max_age_hours=240)

        return {
            "sim_swap_24h": sim,
            "sim_swap_7d": sim_7d,
            "device_swap": device,
        }


camara_service = CamaraService()
