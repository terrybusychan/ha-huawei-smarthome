"""User-contributed protocol for Huawei product 2MZN (小豚当家室外摄像头T5 3K双摄版).

产品: 小豚当家室外摄像头 T5 3K 双摄版
厂商: 智多豚 (dophigo)
型号: XT-H40 (deviceTypeId 008, 网络摄像头, WiFi, uiType PLUGIN)

本适配器遵循项目规范：单品协议行为全部硬编码在本文件内，
不跨产品复用，不做未经 Profile/真机证据支持的推断。

=====================================================================
Profile 服务一览（含未映射项）
=====================================================================
  switch.on              bool   RW  1=开 0=关  摄像头开关(0=待机)  -> camera_switch
  videoSwitch.on         bool   RW  1=开 0=关  摄像/录像开关       -> video_switch
  shootSwitch.on         bool   RW  1=开 0=关  拍照(抓拍)开关      -> shoot_switch

  alarmEvent.alarm         bool R 1=有告警 0=无告警               -> alarm (motion)
  alarmEvent.videoAlarm    bool R 视频检测                        -> video_alarm
  alarmEvent.humanBodyAlarm bool R 人形检测                       -> human_body_alarm
  alarmEvent.babyCryAlarm  bool R 婴儿哭声                        -> baby_cry_alarm
  alarmEvent.auxiliaryFireAlarm bool R 辅助火焰检测               -> fire_alarm
  alarmEvent.carAlarm      bool R 车辆检测                        -> vehicle_alarm
  alarmEvent.audioAlarm    bool R 声音检测                        -> audio_alarm
  alarmEvent.animalAlarm   bool R 动物检测                        -> animal_alarm
  alarmEvent.alarmId       string RW 事件抓拍ID                   参见下方"为什么不映射"
  alarmEvent.id            string RW 标识                         不映射（无用户语义）

  familiarFaceAlarm.alarm              bool R 熟悉人脸告警        -> familiar_face_alarm
  familiarFaceAlarm.familiarFaceAlarmEvent bool R 告警判断        不映射（与 alarm 重复表达同一事件）
  familiarFaceAlarm.faceName           string R 熟悉人脸名称      -> 作为 alarm 事件属性
  familiarFaceAlarm.alarmId            string RW 抓拍ID           参见下方"为什么不映射"

  strangerFaceAlarm.alarm                 bool R 陌生人脸告警     -> stranger_face_alarm
  strangerFaceAlarm.strangerFaceAlarmEvent bool R 告警判断        不映射（同上）
  strangerFaceAlarm.alarmId               string RW 抓拍ID        参见下方"为什么不映射"

  netInfo.intensity      enum   R  20/40/60/80/100 = 0~4 格信号   -> wifi_signal_level
  netInfo.RSSI           int    R  -100..0 dBm                    -> wifi_rssi
  netInfo.IP             string R  设备 IP                        -> ip_address (diagnostic)
  netInfo.BSSID          string R  路由器 MAC                     -> bssid (diagnostic)
  netInfo.SSID           string RW 路由器 SSID                    -> wifi_ssid (diagnostic)

  update.version         string R  固件版本                       -> firmware_version (diagnostic)
  update.progress        int    R  升级进度 %                     不映射（仅升级过程中有意义）
  update.status          enum   R  0..4 升级状态                  不映射
  update.autoUpdateOn    int    RW 自动升级开关                   不映射（低频运维开关）
  update.bootTime / action / centercapability / matchstatus /
  introduction / checkmatch / on                                  不映射（中枢 OTA 流程，无用户价值）

  visitPoint1..6.move    bool   RW 1=移到该预置点 0=无动作        -> 6 个 button
  visitPoint1..6.enable  bool   RW 1=已配置 0=未配置              -> 作为按钮可用性判断
  visitPoint1..6.name    string RW 预置点名称                     -> 作为按钮名称
  visitPoint1..6.id      string RW 预置点ID                       不映射（插件内部标识）

  logReport.*            4 个字段  R/W 故障上报                  不映射（内部日志通道，无用户价值）
  pushStatus.status      int    W(仅P) 推送配置                  不映射（无 R 权限，读不到）

=====================================================================
为什么不映射 alarmId（事件抓拍 ID）
=====================================================================
Profile 对 alarmId 的描述是：设备触发抓拍/录像后上报该 ID，
**该 ID 会随后续 PUSH 消息携带给华为智慧生活 App 插件**，
由插件再向厂商云端换取图片/视频 URL。

本集成不消费华为的 PUSH 通道，也没有该厂商的云端取图接口，
因此该字符串在本集成内无法解析成任何可用的媒体资源。
把它做成 sensor 只会暴露一串无意义的 ID，故不映射。

同理，本集成**没有 camera 平台**（见 const.PLATFORMS），
无法提供实时画面；摄像头接入以开关 + 告警二进制传感器形式呈现，
这与仓库既有摄像头适配器（prod_113j.py / prod_2LOY.py）保持一致。

=====================================================================
为什么不映射 visitPoint*.id
=====================================================================
该 ID 由 App 插件自行分配，仅用于匹配 App 内的 IFTTT 规则。
集成侧按 sid（visitPoint1..6）区分预置点即可，无需该值。

=====================================================================
真机实测记录
=====================================================================
[已实测] 预置点按钮的报文类型必须为数值 1，不能是字符串 "1"。
    现象（修复前）：按下"预置点2"按钮报
        SmartHome command rejected: sid=visitPoint2 errcode=16001
    原因：Profile 的 visitPoint*.move 虽然带 enumList（enumVal 为字符串
        "1"），但 characteristicType 是 bool，真机/云端只接受数值。
        修复前直接把枚举标签字符串 "1" 当报文值发出，被云端拒绝。
    修复：新增 _coerce_payload_value()，按 characteristicType 做数值化
        （bool/int/integer/enum → 数字），与 prod_2g4n.py 的处理一致。
        同一处理也应用到 switch / videoSwitch / shootSwitch 的 on 字段。
    参考：仓库内所有已接入的摄像头适配器（22Q4 / 2C60 / 2NPA / 2poo）
        均发送整数 1。

=====================================================================
尚未验证（需真机确认）
=====================================================================
[ ] 状态读取：全部字段均未在真机上实测，仅依据 Profile 权限/枚举推导。
[ ] 控制命令：switch / videoSwitch / shootSwitch 的 on 写入尚未实测；
    visitPoint*.move 的**类型**已修复，但修复后是否成功跳转待确认。
[ ] 预置点 move 的自复位行为：Profile 说 move 默认 0、=1 时开始移动。
    本适配器按"一次性动作"处理（写成 button），
    若真机上 move 写入 1 后会保持 1，则该按钮会重复触发，
    此时应改为 switch + turn_off 复位，需真机验证后调整。
[ ] 预置点 enable 的语义：按 Profile 解读为"是否已配置该预置点"。
    命令层未把 enable 作为前置校验（避免误判导致按钮不可用），
    仅在 UI 上作为可用性参考。若真机要求先 enable=1 才能 move，
    需要在此文件补充前置写入步骤。
    注意：若 16001 在修复报文类型后仍然出现，则很可能是"该预置点
    未配置（enable=0）"导致的业务拒绝，需据此调整。
[ ] 告警类字段（humanBodyAlarm 等）的置位时长与复位行为未验证，
    当前直接映射为 binary_sensor 的瞬时状态。
[ ] netInfo 各字段设备是否实际上报未验证；若设备不上报，
    这些实体将长期为 unknown（诊断类，不影响主功能）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

# visitPoint1..6：Profile 固定提供 6 个预置点服务。
_VISIT_POINTS = (1, 2, 3, 4, 5, 6)

# netInfo.intensity：Profile 把信号格数编码为 20/40/60/80/100。
_SIGNAL_LEVELS = {
    20: 0,
    40: 1,
    60: 2,
    80: 3,
    100: 4,
}

# alarmEvent 中所有 report=1 的布尔告警字段。
# (characteristicName, 实体 key, 中文名, device_class)
_ALARM_FIELDS = (
    ("videoAlarm", "video_alarm", "视频检测", "motion"),
    ("humanBodyAlarm", "human_body_alarm", "人形检测", "motion"),
    ("babyCryAlarm", "baby_cry_alarm", "婴儿哭声", "sound"),
    ("auxiliaryFireAlarm", "fire_alarm", "辅助火焰检测", "smoke"),
    ("carAlarm", "vehicle_alarm", "车辆检测", "motion"),
    ("audioAlarm", "audio_alarm", "声音检测", "sound"),
    ("animalAlarm", "animal_alarm", "动物检测", "motion"),
)


def _bool(value: Any) -> bool | None:
    """Decode a Huawei bool/enum characteristic into a Python bool."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.casefold() in {"1", "true", "on"}:
            return True
        if value.casefold() in {"0", "false", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _text(value: Any) -> str | None:
    """Return a non-empty string, otherwise ``None``."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _field(
    profile: Mapping[str, Any] | None,
    sid: str,
    name: str,
) -> Mapping[str, Any] | None:
    """Return one Profile characteristic definition, if declared."""

    if not isinstance(profile, Mapping):
        return None
    for service in profile.get("services", ()):
        if not isinstance(service, Mapping) or service.get("serviceId") != sid:
            continue
        for field in service.get("characteristics", ()):
            if (
                isinstance(field, Mapping)
                and field.get("characteristicName") == name
            ):
                return field
        return None
    return None


def _coerce_payload_value(value: Any, field: Mapping[str, Any] | None) -> Any:
    """Encode a command value using the Profile-declared characteristic type.

    2MZN 的 ``visitPoint*.move`` 虽然带 enumList，但 ``characteristicType``
    是 ``bool``，真机只接受**数值** 1。Profile 的 ``enumVal`` 是字符串
    ``"1"``，若原样发送会被云端拒绝：

        HuaweiCommandRejectedError: sid=visitPoint2 errcode=16001

    因此按 characteristicType 做数值化（与 prod_2g4n.py 的处理一致），
    bool/int/integer/enum 一律转成数字；string 及未知类型保持原值。
    """

    if not isinstance(field, Mapping):
        return value
    data_type = str(field.get("characteristicType") or "").casefold()
    if data_type in {"bool", "int", "integer", "enum"}:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else number
    return value


def _profile_enum_value(
    field: Mapping[str, Any] | None,
    fallback: Any,
) -> Any:
    """Return the Profile-declared enum value matching ``fallback``.

    按 characteristicType 编码后返回，保证发出的报文类型与 Profile 一致。
    """

    raw: Any = fallback
    if isinstance(field, Mapping):
        for option in field.get("enumList", ()):
            if not isinstance(option, Mapping):
                continue
            candidate = option.get("enumVal")
            if candidate is not None and str(candidate) == str(fallback):
                raw = candidate
                break
    return _coerce_payload_value(raw, field)


def _alarm_state(context: DeviceContext) -> Mapping[str, Any]:
    """Expose the aggregated alarm flag plus any capturable metadata."""

    attributes: dict[str, Any] = {}
    face_name = _text(context.value("familiarFaceAlarm", "faceName"))
    if face_name is not None:
        # Only meaningful while a familiar-face alarm is present.
        if _bool(context.value("familiarFaceAlarm", "alarm")) is True:
            attributes["face_name"] = face_name
    return {
        "is_on": _bool(context.value("alarmEvent", "alarm")),
        "extra_state_attributes": attributes or None,
    }


def _make_alarm_sensor(
    context: DeviceContext,
    sid: str,
    field: str,
    key: str,
    name: str,
    device_class: str,
) -> EntitySpec:
    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"is_on": _bool(device.value(sid, field))}

    return EntitySpec(
        platform="binary_sensor",
        key=key,
        name=name,
        state=state,
        metadata={"device_class": device_class},
    )


def _make_visit_point_button(
    context: DeviceContext,
    index: int,
) -> EntitySpec:
    """One 预置点 action button writing ``visitPointN.move = 1``."""

    sid = f"visitPoint{index}"
    field = _field(context.profile, sid, "move")
    # Profile 声明 move 的枚举 1=移到该预置点。优先取 Profile 的枚举值，
    # 字段缺失时才回退到 1（与 prod_2g4n.py 的处理方式一致）。
    move_value = _profile_enum_value(field, "1")

    async def move(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {"move": move_value})

    def availability(device: DeviceContext) -> bool:
        # enable=1 表示用户已配置该预置点；未配置时按钮仍可见但不可用。
        if not device.available:
            return False
        return _bool(device.value(sid, "enable")) is not False

    def state(device: DeviceContext) -> Mapping[str, Any]:
        # button 平台不使用 state 的取值，只要求可调用；
        # 预置点名称与配置状态通过 extra_state_attributes 呈现。
        name = _text(device.value(sid, "name"))
        enabled = _bool(device.value(sid, "enable"))
        attributes: dict[str, Any] = {}
        if name is not None:
            attributes["preset_name"] = name
        if enabled is not None:
            attributes["configured"] = enabled
        return {"extra_state_attributes": attributes or None}

    return EntitySpec(
        platform="button",
        key=f"visit_point_{index}",
        name=f"预置点{index}",
        state=state,
        actions={"press": move},
        availability=availability,
    )


def _signal_level(context: DeviceContext) -> int | None:
    """Map the Profile's 20/40/60/80/100 encoding to a 0..4 level."""

    value = _number(context.value("netInfo", "intensity"))
    if value is None:
        return None
    return _SIGNAL_LEVELS.get(int(value))


def _make_switch(
    context: DeviceContext,
    sid: str,
    key: str,
    name: str,
) -> EntitySpec:
    # on 字段同样是 bool + enumList，取值经 Profile 类型编码，
    # 避免把枚举标签字符串直接当报文值发出。
    field = _field(context.profile, sid, "on")
    on_value = _profile_enum_value(field, 1)
    off_value = _profile_enum_value(field, 0)

    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"is_on": _bool(device.value(sid, "on"))}

    async def turn_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {"on": on_value})

    async def turn_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {"on": off_value})

    return EntitySpec(
        platform="switch",
        key=key,
        name=name,
        state=state,
        actions={"turn_on": turn_on, "turn_off": turn_off},
    )


class Product2MZNAdapter:
    """Keep all 2MZN entity and command choices in this file."""

    prod_id = "2MZN"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        profile = context.profile
        if profile is None:
            return ()

        entities: list[EntitySpec] = []

        # --- 主控开关 -------------------------------------------------
        if context.has_service("switch"):
            entities.append(
                _make_switch(context, "switch", "camera", "摄像头开关")
            )
        if context.has_service("videoSwitch"):
            entities.append(
                _make_switch(context, "videoSwitch", "video", "摄像开关")
            )
        if context.has_service("shootSwitch"):
            entities.append(
                _make_switch(context, "shootSwitch", "shoot", "拍照开关")
            )

        # --- 告警 -----------------------------------------------------
        if context.has_service("alarmEvent"):
            entities.append(
                EntitySpec(
                    platform="binary_sensor",
                    key="alarm",
                    name="告警",
                    state=_alarm_state,
                    metadata={"device_class": "motion"},
                )
            )
            for field, key, name, device_class in _ALARM_FIELDS:
                entities.append(
                    _make_alarm_sensor(
                        context,
                        "alarmEvent",
                        field,
                        key,
                        name,
                        device_class,
                    )
                )

        if context.has_service("familiarFaceAlarm"):
            entities.append(
                _make_alarm_sensor(
                    context,
                    "familiarFaceAlarm",
                    "alarm",
                    "familiar_face_alarm",
                    "熟悉人脸告警",
                    "motion",
                )
            )
        if context.has_service("strangerFaceAlarm"):
            entities.append(
                _make_alarm_sensor(
                    context,
                    "strangerFaceAlarm",
                    "alarm",
                    "stranger_face_alarm",
                    "陌生人脸告警",
                    "motion",
                )
            )

        # --- 预置点（最多 6 个，按 Profile 实际提供的服务创建） --------
        for index in _VISIT_POINTS:
            if context.has_service(f"visitPoint{index}"):
                entities.append(_make_visit_point_button(context, index))

        # --- 网络诊断 -------------------------------------------------
        if context.has_service("netInfo"):
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="wifi_signal_level",
                    name="Wi-Fi 信号格数",
                    state=lambda device: {
                        "native_value": _signal_level(device)
                    },
                    metadata={
                        "state_class": "measurement",
                        "entity_category": "diagnostic",
                    },
                )
            )
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="wifi_rssi",
                    name="Wi-Fi 信号强度",
                    state=lambda device: {
                        "native_value": _number(device.value("netInfo", "RSSI"))
                    },
                    metadata={
                        "device_class": "signal_strength",
                        "unit": "dBm",
                        "state_class": "measurement",
                        "entity_category": "diagnostic",
                    },
                )
            )
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="ip_address",
                    name="IP 地址",
                    state=lambda device: {
                        "native_value": _text(device.value("netInfo", "IP"))
                    },
                    metadata={"entity_category": "diagnostic"},
                )
            )
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="wifi_ssid",
                    name="Wi-Fi SSID",
                    state=lambda device: {
                        "native_value": _text(device.value("netInfo", "SSID"))
                    },
                    metadata={"entity_category": "diagnostic"},
                )
            )
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="bssid",
                    name="路由器 BSSID",
                    state=lambda device: {
                        "native_value": _text(device.value("netInfo", "BSSID"))
                    },
                    metadata={"entity_category": "diagnostic"},
                )
            )

        # --- 固件版本（诊断） -----------------------------------------
        if context.has_service("update"):
            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="firmware_version",
                    name="固件版本",
                    state=lambda device: {
                        "native_value": _text(device.value("update", "version"))
                    },
                    metadata={"entity_category": "diagnostic"},
                )
            )

        return tuple(entities)


ADAPTER = Product2MZNAdapter()
