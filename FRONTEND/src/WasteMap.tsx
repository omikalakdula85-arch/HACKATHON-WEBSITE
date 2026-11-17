import { divIcon } from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMapEvents,
} from "react-leaflet";
import type { FleetRoute, Location, Report, Vehicle } from "./types";

const ROUTE_COLORS = ["#54d6a0", "#78a8ff", "#ffba69", "#d18bff"];
const truckIcon = divIcon({
  className: "truck-icon-shell",
  html: '<div class="truck-icon">T</div>',
  iconSize: [32, 32],
  iconAnchor: [16, 16],
});

interface WasteMapProps {
  locations?: Location[];
  reports?: Report[];
  routes?: FleetRoute[];
  vehicles?: Vehicle[];
  selectedPoint?: { latitude: number; longitude: number } | null;
  truckPosition?: { latitude: number; longitude: number } | null;
  interactive?: boolean;
  onChoosePoint?: (point: { latitude: number; longitude: number }) => void;
}

function MapClickHandler({ onChoosePoint }: { onChoosePoint?: WasteMapProps["onChoosePoint"] }) {
  useMapEvents({
    click(event) {
      onChoosePoint?.({
        latitude: Number(event.latlng.lat.toFixed(6)),
        longitude: Number(event.latlng.lng.toFixed(6)),
      });
    },
  });
  return null;
}

export default function WasteMap({
  locations = [],
  reports = [],
  routes = [],
  vehicles = [],
  selectedPoint = null,
  truckPosition = null,
  interactive = false,
  onChoosePoint,
}: WasteMapProps) {
  return (
    <div className={`waste-map${interactive ? " waste-map--interactive" : ""}`}>
      <MapContainer
        center={[6.899, 79.872]}
        zoom={12}
        scrollWheelZoom
        className="leaflet-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {interactive && <MapClickHandler onChoosePoint={onChoosePoint} />}
        {routes.map((route, index) => (
          <Polyline
            key={route.id}
            positions={route.waypoints.map((point) => [point.latitude, point.longitude])}
            pathOptions={{
              color: ROUTE_COLORS[index % ROUTE_COLORS.length],
              weight: 4,
              opacity: 0.78,
              dashArray: route.status === "completed" ? "5 8" : undefined,
            }}
          >
            <Popup>{route.vehicleName} · {route.distanceKm.toFixed(1)} km</Popup>
          </Polyline>
        ))}
        {locations.map((location) => (
          <CircleMarker
            key={location.id}
            center={[location.latitude, location.longitude]}
            radius={6 + Math.min(location.fillLevelPercent / 30, 4)}
            pathOptions={{
              color: location.fillLevelPercent >= 85 ? "#ff8c7a" : "#62d9a1",
              fillColor: location.fillLevelPercent >= 85 ? "#ff8c7a" : "#62d9a1",
              fillOpacity: 0.8,
              weight: 1.5,
            }}
          >
            <Popup>
              <strong>{location.name}</strong>
              <br />
              Predicted fill: {location.fillLevelPercent}%
              <br />
              Est. waste: {location.estimatedWasteKg} kg
            </Popup>
          </CircleMarker>
        ))}
        {reports.map((report) => (
          <CircleMarker
            key={report.id}
            center={[report.latitude, report.longitude]}
            radius={8}
            pathOptions={{
              color: report.status === "Collected" ? "#8f9daa" : "#f2b84b",
              fillColor: report.status === "Collected" ? "#8f9daa" : "#f2b84b",
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{report.wasteType} · {report.status}</strong>
              <br />
              {report.address || report.description.slice(0, 100)}
              {report.eta && <><br />ETA {report.eta}</>}
            </Popup>
          </CircleMarker>
        ))}
        {vehicles.map((vehicle) => (
          <Marker
            key={vehicle.id}
            position={[vehicle.latitude, vehicle.longitude]}
            icon={truckIcon}
          >
            <Popup>{vehicle.name} · {vehicle.available ? "Available" : "On route"}</Popup>
          </Marker>
        ))}
        {selectedPoint && (
          <Marker position={[selectedPoint.latitude, selectedPoint.longitude]}>
            <Popup>Selected collection location</Popup>
          </Marker>
        )}
        {truckPosition && (
          <Marker
            position={[truckPosition.latitude, truckPosition.longitude]}
            icon={truckIcon}
            zIndexOffset={1000}
          >
            <Popup>Simulated truck position</Popup>
          </Marker>
        )}
      </MapContainer>
      {interactive && <span className="map-pick-hint">Click the map to place your report</span>}
    </div>
  );
}
