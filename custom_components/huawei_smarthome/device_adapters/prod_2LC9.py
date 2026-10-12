"""User-contributed protocol for Huawei product 2LC9 (鸿蒙智选 小豚当家室外摄像头 4G版).

产品: 鸿蒙智选 小豚当家室外摄像头 4G版
厂商: 智多豚 (dophigo)
型号: XT-H32 (deviceTypeId 008, 网络摄像头, WiFi, uiType PLUGIN)

本适配器遵循项目规范：单品协议行为全部硬编码在本文件内，
**不跨产品复用**。2LC9 与 2MZN 虽同厂商同设备类型，但服务集合不同
（本机有 4G 流量服务、无云台预置点；2MZN 有 6 个预置点、无 4G），
因此各自独立实现，不提取公共基类，也不共享映射表。

=====================================================================
Profile 服务一览（含未映射项）
=====================================================================
  switch.on              bool  RW 1=开 0=关(待机)  摄像头开关 -> camera_switch
  shootSwitch.on         bool  RW 抓拍照开关          -> shoot_switch
  videoSwitch.on         bool  RW 摄像开关            -> video_switch

  alarmEvent.animalAlarm       bool RW 动物检测       -> animal_alarm
  alarmEvent.humanBodyAlarm    bool RW 人形检测       -> human_body_alarm
  alarmEvent.videoAlarm        bool R  视频检测       -> video_alarm
  alarmEvent.audioAlarm        bool R  声音检测       -> audio_alarm
  alarmEvent.babyCryAlarm      bool R  婴儿哭声检测   -> baby_cry_alarm
  alarmEvent.auxiliaryFireAlarm bool R 火焰检测       -> fire_alarm
  alarmEvent.alarmId           string RW 告警信息     不映射为实体，见下方说明
  另有一个 alarm 事件实体（event 平台），每次告警推送触发一次

  lteService.expireDays        int  R 0~30           -> lte_expire_days
  lteService.expireStatus      int  R 0~30           -> lte_expire_status
  lteService.alarmId           string R PUSH消息id   不映射（无用户语义）

  netInfo.intensity      enum  R 20/40/60/80/100     -> wifi_signal_level
  netInfo.RSSI           int   R -100~0 dB           -> wifi_rssi
  netInfo.IP/SSID/BSSID  string R                    -> 诊断传感器

  update.version         string R 固件版本            -> firmware_version
  update.progress/bootTime/introduction/action       不映射（OTA 流程）

  deviceInfo.id / verifyId   string R                不映射（厂商云端凭据）
  pushStatus.status          int    RW               不映射（见下方说明）

=====================================================================
为什么告警字段既做 binary_sensor 又做 event
=====================================================================
alarmEvent 是**一次性信号**：设备检测到目标时推送一次，之后**不会**
推送"已清除"值。若只做 binary_sensor，第一次告警后会永久停在 on，
后续同类告警因为状态没变化（on→on）而无法再次触发自动化。

因此本适配器同时提供：
  1. binary_sensor：描述"最近一次上报的告警是什么"（可能长期保持 on）；
  2. event 实体  ：每次被接受的告警推送都触发一次事件，自动化应基于它，
     并可读取 alarm_id 区分不同事件。

这与仓库既有摄像头适配器（prod_2gaf.py）的处理方式一致。

注意：animalAlarm 与 humanBodyAlarm 在本 Profile 是 RW（可写），
说明它们兼具"检测使能开关"语义；但 Profile 的 attrName 写的是
"动物检测/人形检测"且 descCh 明确"仅做IFTTT条件"，无法确定写入
1/0 是"使能检测"还是"模拟告警"。**在缺乏真机证据的情况下不暴露写
命令**，只做只读告警呈现（符合 Skill 的失败关闭原则）。

=====================================================================
为什么不映射 alarmId / deviceInfo / pushStatus
=====================================================================
1. alarmEvent.alarmId 与 lteService.alarmId：Profile 说明该 ID 由设备
   上报后**随 PUSH 消息交给华为智慧生活 App 插件**，由插件向厂商云端
   换取图片/视频 URL。本集成不消费华为 PUSH 通道，也没有该厂商的取图
   接口，做成 sensor 只会暴露一串无意义字符串。
   它仍会作为 event 实体的属性（alarm_id）供自动化关联使用。

2. deviceInfo.id / verifyId：厂商云端的设备注册 ID 与插件校验码，
   属于凭据类信息，暴露到 HA 状态机没有用户价值且有泄露风险。

3. pushStatus.status：Profile 中该服务**未声明 permission，
   也未声明 method 之外的任何元数据**（无 attrName/descCh/enumList），
   取值域 0~65535 无枚举说明。含义未知，按失败关闭原则不映射。

4. lteService.expireStatus 同样是纯 int（0~30）且无枚举说明，
   仅作为原始数值输出；若真机确认为状态码枚举，后续可改为 select。

=====================================================================
报文类型（沿用 2MZN 的实测教训）
=====================================================================
Profile 的 enumList 里 ``enumVal`` 一律是**字符串**（如 ``"1"``），
但 characteristicType 是 bool/enum/int，真机只接受**数值**。
直接把枚举字符串当报文值发送会被云端拒绝（errcode=16001）。
因此本文件所有写命令都经 _coerce() 按 characteristicType 数值化，
取值本身从 Profile 的 enumList 读取，不硬编码。

注：本机 alarmEvent 下有若干字段 permission 为空字符串（供应商资料
填写不完整），本适配器一律按"只读"处理，绝不尝试写入。

=====================================================================
没有 camera 平台实体（硬限制，非漏适配）
=====================================================================
本仓库未注册 camera 平台（见 const.PLATFORMS），且本 Profile 也**没有**
任何快照 URL / 视频流地址特征。因此无法在 HA 中呈现实时画面或抓拍图。
按仓库"避免错误状态映射"的原则，本适配器把云端真实可读/可写的控制与
侦测能力映射到受支持的平台：switch / binary_sensor / event / sensor。

=====================================================================
尚未验证（需真机确认）
=====================================================================
[ ] 状态读取：全部字段未在真机实测，仅依据 Profile 权限/枚举推导。
[ ] 控制命令：switch / shootSwitch / videoSwitch 的 on 写入未实测。
[ ] 告警事件：event 实体依赖 deviceDataChanged 推送，需真机确认
    设备上报 alarmEvent 的字段形态（本机 videoAlarm 等为只读 R，
    animalAlarm/humanBodyAlarm 为 RW）。
[ ] 4G 流量：lteService.expireDays / expireStatus 的单位与语义未知
    （Profile 未给 attrName/单位）。当前按原始数值输出：
    expireDays 推测为"剩余天数"，expireStatus 推测为状态码，均未验证。
    若真机显示异常，请提供上报值以便修正。
[ ] netInfo 各字段设备是否实际上报未验证；若不上报将长期为 unknown
    （诊断类，不影响主功能）。
[ ] humanBodyAlarm / animalAlarm 的写入语义未验证，故未暴露写命令。
    若真机确认写 1/0 是"检测使能开关"，可新增对应 switch 实体。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

_ALARM_SID = "alarmEvent"

# netInfo.intensity：Profile 把信号格数编码为 20/40/60/80/100。
_SIGNAL_LEVELS = {20: 0, 40: 1, 60: 2, 80: 3, 100: 4}

# alarmEvent 中需要以 binary_sensor + event 暴露的告警字段。
# (characteristicName, event_type, 中文名, device_class)
_ALARM_FIELDS = (
    ("humanBodyAlarm", "human_body", "人形检测", "motion"),
    ("animalAlarm", "animal", "动物检测", "motion"),
    ("videoAlarm", "video", "视频检测", "motion"),
    ("audioAlarm", "audio", "声音检测", "sound"),
    ("babyCryAlarm", "baby_cry", "婴儿哭声检测", "sound"),
    ("auxiliaryFireAlarm", "fire", "火焰检测", "smoke"),
)

# 需要以 switch 实体暴露的服务（sid, key, 名称）
_SWITCH_SPECS = (
    ("switch", "camera", "摄像头开关"),
    ("videoSwitch", "video", "摄像开关"),
    ("shootSwitch", "shoot", "拍照开关"),
)

# alarmId 中分隔"事件标识"与"时间戳"的分隔符（沿用 prod_2gaf.py 的约定）。
_ALARM_ID_SEPARATOR = "::"


# ---------------------------------------------------------------------
# 取值解码
# ---------------------------------------------------------------------
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


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(round(number))


def _text(value: Any) -> str | None:
    """Return a non-empty string, otherwise ``None``."""

    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


# ---------------------------------------------------------------------
# Profile 读取与报文编码
# ---------------------------------------------------------------------
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


def _is_writable(field: Mapping[str, Any] | None) -> bool:
    """Return whether the Profile declares a write capability."""

    if not isinstance(field, Mapping):
        return False
    return "W" in str(field.get("method") or "")


def _coerce(value: Any, field: Mapping[str, Any] | None) -> Any:
    """Encode a command value using the Profile-declared characteristic type.

    Profile 的 enumList 里 enumVal 是字符串，但 bool/enum/int 类字段
    真机只接受数值（否则云端回 errcode=16001）。此处统一数值化。
    """

    if not isinstance(field, Mapping):
        return value
    data_type = str(field.get("characteristicType") or "").casefold()
    if data_type in {"bool", "int", "integer", "enum"}:
        number = _number(value)
        if number is None:
            return value
        return int(number) if number.is_integer() else number
    if data_type in {"float", "double", "number"}:
        number = _number(value)
        return value if number is None else number
    return value


def _enum_value(
    field: Mapping[str, Any] | None,
    wanted: Any,
    fallback: Any,
) -> Any:
    """Resolve the Profile-declared enum value matching ``wanted``."""

    raw: Any = fallback
    if isinstance(field, Mapping):
        for option in field.get("enumList", ()):
            if not isinstance(option, Mapping):
                continue
            candidate = option.get("enumVal")
            if candidate is None:
                continue
            if str(candidate) == str(wanted):
                raw = candidate
                break
            if str(wanted) in {
                str(option.get("descCh") or ""),
                str(option.get("descEn") or ""),
            }:
                raw = candidate
                break
    return _coerce(raw, field)


# ---------------------------------------------------------------------
# 告警事件解码
# ---------------------------------------------------------------------
def _alarm_event_decoder(
    device: DeviceContext,
    sid: str,
    data: Mapping[str, Any],
    timestamp: str | None,
) -> list[tuple[str, Mapping[str, Any]]]:
    """Turn one ``alarmEvent`` push into Home Assistant events.

    ``alarmEvent`` is a one-shot signal: the device pushes it when something
    is detected and never sends the cleared value.  The binary_sensors
    declared beside this decoder therefore only describe *what was last
    reported* and cannot drive an automation that must run on every
    detection -- a later detection that sets the same field produces no
    state change at all.

    This decoder supplies the missing half: each accepted push is reported as
    an event, so an automation can trigger on every occurrence and read
    ``alarm_id`` to tell them apart.
    """

    if sid != _ALARM_SID:
        return []

    alarm_id = data.get("alarmId")
    alarm_ref = str(alarm_id) if alarm_id is not None else None
    detected_at = None
    if isinstance(alarm_id, str) and _ALARM_ID_SEPARATOR in alarm_id:
        detected_at = alarm_id.rsplit(_ALARM_ID_SEPARATOR, 1)[-1] or None

    events: list[tuple[str, Mapping[str, Any]]] = []
    for field_name, event_type, _name, _device_class in _ALARM_FIELDS:
        # Any field the Profile declares as 0/1 may arrive as a bool, an int
        # or a numeric string, so ``_bool`` is used rather than a truthiness
        # test that would treat the string "0" as raised.
        if _bool(data.get(field_name)) is not True:
            continue
        # A single push can carry several raised fields, so every raised one
        # is reported; the shared alarm id keeps them recognisable as one
        # occurrence.
        events.append(
            (
                event_type,
                {
                    "alarm_id": alarm_ref,
                    "detected_at": detected_at,
                    "received_at": timestamp,
                    "camera": device.name,
                },
            )
        )
    return events


# ---------------------------------------------------------------------
# 实体构建
# ---------------------------------------------------------------------
def _make_switch(
    context: DeviceContext,
    sid: str,
    key: str,
    name: str,
) -> EntitySpec | None:
    """One switch backed by an RW ``on`` characteristic."""

    field = _field(context.profile, sid, "on")
    if not _is_writable(field):
        return None
    on_value = _enum_value(field, 1, 1)
    off_value = _enum_value(field, 0, 0)

    async def turn_on(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {"on": on_value})

    async def turn_off(device: DeviceContext, _data: Mapping[str, Any]) -> None:
        await device.async_send_service(sid, {"on": off_value})

    return EntitySpec(
        platform="switch",
        key=key,
        name=name,
        state=lambda device: {"is_on": _bool(device.value(sid, "on"))},
        actions={"turn_on": turn_on, "turn_off": turn_off},
    )


def _make_alarm_sensor(
    sid: str,
    field_name: str,
    key: str,
    name: str,
    device_class: str,
) -> EntitySpec:
    """One read-only alarm flag.

    Kept as a ``binary_sensor`` because it describes the latest reported
    detection; the paired ``event`` entity carries the per-occurrence signal.
    """

    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"is_on": _bool(device.value(sid, field_name))}

    return EntitySpec(
        platform="binary_sensor",
        key=key,
        name=name,
        state=state,
        metadata={"device_class": device_class},
    )


def _make_alarm_event() -> EntitySpec:
    """One ``event`` entity firing on every accepted alarm push."""

    return EntitySpec(
        platform="event",
        key="alarm",
        name="告警事件",
        state=lambda device: {},
        metadata={
            "event_types": [event_type for _, event_type, _, _ in _ALARM_FIELDS]
        },
        event_decoder=_alarm_event_decoder,
    )


def _make_sensor(
    sid: str,
    field_name: str,
    key: str,
    name: str,
    *,
    unit: str | None = None,
    device_class: str | None = None,
    state_class: str | None = None,
    entity_category: str | None = None,
    decode: Any = None,
) -> EntitySpec:
    decoder = decode or (lambda value: _int(value))

    def state(device: DeviceContext) -> Mapping[str, Any]:
        return {"native_value": decoder(device.value(sid, field_name))}

    metadata: dict[str, Any] = {}
    if unit is not None:
        metadata["unit"] = unit
    if device_class is not None:
        metadata["device_class"] = device_class
    if state_class is not None:
        metadata["state_class"] = state_class
    if entity_category is not None:
        metadata["entity_category"] = entity_category

    return EntitySpec(
        platform="sensor",
        key=key,
        name=name,
        state=state,
        metadata=metadata,
    )


class Product2LC9Adapter:
    """Keep all 2LC9 entity and command choices in this file."""

    prod_id = "2LC9"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        profile = context.profile
        if profile is None:
            return ()

        entities: list[EntitySpec] = []

        # --- 控制开关 -------------------------------------------------
        for sid, key, name in _SWITCH_SPECS:
            if not context.has_service(sid):
                continue
            spec = _make_switch(context, sid, key, name)
            if spec is not None:
                entities.append(spec)

        # --- 告警：binary_sensor（最近状态） + event（每次触发） ------
        if context.has_service(_ALARM_SID):
            for field_name, _event_type, name, device_class in _ALARM_FIELDS:
                field = _field(profile, _ALARM_SID, field_name)
                if field is None:
                    continue
                entities.append(
                    _make_alarm_sensor(
                        _ALARM_SID,
                        field_name,
                        f"{field_name}",
                        name,
                        device_class,
                    )
                )
            entities.append(_make_alarm_event())

        # --- 4G 流量（诊断） ------------------------------------------
        if context.has_service("lteService"):
            # Profile 未给出 attrName/unit，按原始数值输出并标注为诊断。
            for field_name, key, name in (
                ("expireDays", "lte_expire_days", "4G 流量剩余天数"),
                ("expireStatus", "lte_expire_status", "4G 流量状态"),
            ):
                if _field(profile, "lteService", field_name) is None:
                    continue
                entities.append(
                    _make_sensor(
                        "lteService", field_name, key, name,
                        state_class="measurement",
                        entity_category="diagnostic",
                        decode=_int,
                    )
                )

        # --- 网络诊断 -------------------------------------------------
        if context.has_service("netInfo"):
            entities.append(
                _make_sensor(
                    "netInfo", "intensity", "wifi_signal_level",
                    "Wi-Fi 信号格数",
                    state_class="measurement", entity_category="diagnostic",
                    decode=lambda value: _SIGNAL_LEVELS.get(_int(value) or -1),
                )
            )
            entities.append(
                _make_sensor(
                    "netInfo", "RSSI", "wifi_rssi", "Wi-Fi 信号强度",
                    unit="dB", device_class="signal_strength",
                    state_class="measurement", entity_category="diagnostic",
                    decode=_int,
                )
            )
            entities.append(
                _make_sensor(
                    "netInfo", "IP", "ip_address", "IP 地址",
                    entity_category="diagnostic", decode=_text,
                )
            )
            entities.append(
                _make_sensor(
                    "netInfo", "SSID", "wifi_ssid", "Wi-Fi SSID",
                    entity_category="diagnostic", decode=_text,
                )
            )
            entities.append(
                _make_sensor(
                    "netInfo", "BSSID", "bssid", "路由器 BSSID",
                    entity_category="diagnostic", decode=_text,
                )
            )

        # --- 固件版本（诊断） -----------------------------------------
        if context.has_service("update"):
            entities.append(
                _make_sensor(
                    "update", "version", "firmware_version", "固件版本",
                    entity_category="diagnostic", decode=_text,
                )
            )

        return tuple(entities)


ADAPTER = Product2LC9Adapter()
