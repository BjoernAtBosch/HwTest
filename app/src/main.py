# Copyright (c) 2023 Robert Bosch GmbH
#
# This program and the accompanying materials are made available under the
# terms of the Apache License, Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# SPDX-License-Identifier: Apache-2.0


# pylint: disable=C0103, C0413, E1101
import asyncio
import logging
import signal
from enum import Enum

from vehicle import Vehicle, vehicle  # type: ignore
from velocitas_sdk.util.log import (  # type: ignore
    get_opentelemetry_log_factory,
    get_opentelemetry_log_format,
)
from velocitas_sdk.vdb.reply import DataPointReply
from velocitas_sdk.vehicle_app import VehicleApp

# Configure the VehicleApp logger with the necessary log config and level.
logging.setLogRecordFactory(get_opentelemetry_log_factory())
logging.basicConfig(format=get_opentelemetry_log_format())
logging.getLogger().setLevel("DEBUG")
logger = logging.getLogger(__name__)


class Mode(Enum):
    OFF = 0
    NIGHT_RIDER = 1
    RAINBOW = 2
    FADE_IN = 3


class PassengerWelcomeApp(VehicleApp):
    def __init__(self, vehicle_client: Vehicle):
        super().__init__()
        self.Vehicle = vehicle_client
        self.driver_door = self.Vehicle.Cabin.Door.Row1.Left
        self.driver_seat = self.Vehicle.Cabin.Seat.Row1.Pos1

    async def on_start(self):
        await self.driver_seat.Position.set(0)

        # Callback
        await self.driver_door.IsOpen.subscribe(self.on_door_status_change)

    async def on_door_status_change(self, data: DataPointReply):
        """This will be executed when receiving a new door status update."""
        door_status = data.get(self.driver_door.IsOpen).value

        if door_status:
            await self.Vehicle.set_many().add(self.driver_seat.Position, 1000).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Mode, str(Mode.NIGHT_RIDER.value)
            ).add(self.Vehicle.Cabin.Lights.InteriorLight.Red, 0).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Green, 255
            ).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Blue, 0
            ).add(
                self.Vehicle.Body.Lights.Beam.Low.IsOn, True
            ).apply()
        else:
            await self.Vehicle.set_many().add(
                self.driver_seat.Position, 500
            ).add(self.Vehicle.Cabin.Lights.InteriorLight.Mode, str(Mode.RAINBOW.value)).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Red, 255
            ).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Green, 0
            ).add(
                self.Vehicle.Cabin.Lights.InteriorLight.Blue, 0
            ).apply()
            await asyncio.sleep(2)
            await self.Vehicle.set_many().add(
                self.Vehicle.Cabin.Lights.InteriorLight.Mode, str(Mode.OFF.value)
            ).add(self.Vehicle.Body.Lights.Beam.Low.IsOn, False).apply()


async def main():
    logger.info("Starting PassengerWelcomeApp...")
    vehicle_app = PassengerWelcomeApp(vehicle)
    await vehicle_app.run()


LOOP = asyncio.get_event_loop()
LOOP.add_signal_handler(signal.SIGTERM, LOOP.stop)
LOOP.run_until_complete(main())
LOOP.close()
