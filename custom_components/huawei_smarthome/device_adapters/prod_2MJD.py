"""User-contributed protocol for Huawei product 2MJD (红外万能遥控中心).

产品: 红外万能遥控中心
厂商: 深圳遥看科技有限公司 (yaokan)
型号: YKK-H1025 (deviceTypeId 007, 万能遥控器, WiFi, uiType H5)

本适配器遵循项目规范：单品协议行为全部硬编码在本文件内，
不跨产品复用，不做未经 Profile/真机证据支持的推断。

=====================================================================
★ 这个设备是什么：它不发"状态"，只发"红外码"
=====================================================================
这是**红外遥控中心（IR blaster hub）**：它自己不是空调/电视/机顶盒，
而是通过发射红外码去**遥控别的家电**。这带来三个关键后果：

  1. 它的绝大多数服务是"按键"语义（airKey/TVKey/STBKey/speakerKey/
     projectorKey/purifierKey/mediaKey1~3），一次写入 = 发一次红外码。
     设备**不会回报被控家电的真实状态**（因为它也收不到）。
  2. Profile 里这些服务只有 ``action``/``mode``/``mute``/``on`` 等
     **写入字段**，没有对应的状态回读字段。
  3. 因此**不能把它们做成 switch/select**——那会造出"看起来有状态、
     实际永远不同步"的假实体。HA 的开关一旦被点开就会显示"开"，
     而电视到底开没开设备根本不知道。

按仓库"避免错误状态映射"的原则，本适配器：
  * **不暴露任何 switch/select 去代表被控家电**；
  * 把"发码"类服务暴露为 **button**（瞬时动作，语义正确）；
  * 只把**设备自身**的真实状态做成实体（匹配状态、WiFi、固件版本）；
  * 空调类指令虽是连续参数，但同样无回读 → 见下方专门说明。

=====================================================================
Profile 服务一览（含未映射项）
=====================================================================
  设备自身状态（可读、有意义）：
    status.status          enum  RW 0=匹配中 100=匹配成功 200=匹配失败
                                                      -> match_status (sensor)
    netInfo.intensity      enum  R  20/40/60/80/100    -> wifi_signal_level
    netInfo.band           enum  RW 1=2.4G 2=5G        -> wifi_band (select)
    netInfo.RSSI/IP/SSID/BSSID                          -> 诊断传感器
    update.version         string R 固件版本             -> firmware_version

  设备自身开关（有真实回读）：
    indicatorSwitch.on     bool  RW 指示灯开关            -> indicator (switch)

  发码类（无回读 → button，不建状态实体）：
    airKey.*        空调指令（on/mode/gear/target/airSwing）  见下方专门说明
    TVKey.*         电视指令（on/mute/action/channel）        -> 不映射
    STBKey.*        机顶盒指令（on/mute/action/channel）      -> 不映射
    speakerKey.*    音响指令（on/mute/action）                -> 不映射
    projectorKey.*  投影仪指令（on/mute/action/channel）      -> 不映射
    purifierKey.*   净化器指令（on/mode）                    -> 不映射
    mediaKey/mediaKey1~3  自定义遥控器按键                    -> 不映射
    fanSwitch.on / fanMode.mode   风扇开关/风扇控制            -> 不映射
    fanSwitch.controlSource       控制源（字符串）             -> 不映射

  配对/配置类（不映射）：
    rcList.*        遥控器列表（array[object]，13 字段）      不映射，见下方
    customKey.*     自定义按键名称（5 个字符串 + devid）      不映射，见下方
    matchedCap.jsonstr  红外码下发（12000 字符 JSON 串）      不映射，见下方
    delay1.*        倒计时关机（字符串 + action）            不映射，见下方
    batchCmd.*      批控（9 字段，含重复 characteristicName） 不映射，见下方
    backup.*        配置备份（array[object]）                不映射，见下方
    update.on/action/progress/bootTime/introduction          不映射（OTA 运维）

=====================================================================
★ 空调指令（airKey）为什么也没有做成 climate
=====================================================================
airKey 有完整的一组参数（on / mode / gear / target / airSwing），
看起来像一台空调，而且本仓库已有 115J（空调伴侣）做成 climate 的先例。
但**本机与 115J 有本质区别**：

  * 115J 是**带功率计量的空调伴侣**，它自己串在空调电源上，
    能真实测到功率/工作时长，Profile 里也确实有回读字段；
  * **2MJD 只是红外发射器**：写入 airKey = 朝空调发一帧红外码。
    它既不知道空调当前是开是关，也不知道温度设成了多少
    （Profile 里 airKey 只有可写字段，**没有任何状态回读字段**）。

若做成 climate，HA 会显示一个"当前模式/当前温度/开关"的仪表盘，
而这些值**全部是凭空捏造的**（我们只能记住"上次发过什么"）。
一旦用户用原装遥控器改了空调，HA 的显示就会与现实不符，
比没有实体更糟。

因此本适配器**不暴露 climate**。若确实需要红外控空调，建议用仓库
既有的通用做法：在华为智慧生活 App 里把红外码配好，再用 App 侧
场景/自动化触发；或在 HA 里用 script + button 组合（需另行扩展）。

=====================================================================
为什么不映射 rcList / customKey / matchedCap / delay1 / batchCmd / backup
=====================================================================
1. ``rcList.list``：被控设备列表（array[object]，每个元素 13 个字段：
   on/rid/devId/deviceName/name/zip/threshold/brightness/index/
   colorTemperature/maximum/tid/current）。它是**遥控器的配置数据**，
   且 rid/zip 等是厂商码库的内部编码，暴露到 HA 无用户价值；
   写入还需整体回写 13 个字段，本集成没有该事务能力。

2. ``customKey.name1~name5`` / ``devid`` / ``index``：自定义按键的
   **名称与设备标识**，属于 App 侧的配置元数据，不是运行状态。

3. ``matchedCap.jsonstr``：一次下发 12000 字符的红外码 JSON。格式
   完全由厂商码库定义（Profile 无任何说明），构造错误会发出错误红外码。

4. ``delay1``：倒计时关机，载体是 ``string``（1000 字符，格式未说明），
   需配合 action 的 更新/新增/删除。格式未知 → 失败关闭。

5. ``batchCmd``：批控服务。**该服务存在结构性缺陷**：
   ``enable`` 这个 characteristicName **出现了两次**——一次是只读
   enum（"support"），一次是可写 int。同一服务内重名字段会让按名字
   取字段的实现产生歧义（本适配器的 _field() 只会返回第一个匹配）。
   加上 action/device 是 12000 字符的 array[object]，
   在语义不明的情况下**不映射**。

6. ``backup``：配置备份列表（array[object]，元素仅 siid 字符串），
   是厂商侧的备份机制，无用户侧价值。

=====================================================================
报文类型（沿用 2MZN 的实测教训）
=====================================================================
Profile 的 enumList 里 ``enumVal`` 一律是**字符串**（如 ``"1"``），
但 characteristicType 是 bool/enum/int，真机只接受**数值**。
直接把枚举字符串当报文值发送会被云端拒绝（errcode=16001）。
因此本文件所有写命令都经 _coerce() 按 characteristicType 数值化。

``_enum_value()`` **只按 enumVal 精确匹配，不做 descCh/descEn
文本回退**——本机多个服务的枚举文案互相重复（如 TVKey/STBKey/
projectorKey 都有"返回/菜单/信号源"），文本回退必然串味
（2QWL 适配中踩过的真实 bug）。

=====================================================================
尚未验证（需真机确认）
=====================================================================
[ ] 状态读取：全部字段未在真机实测，仅依据 Profile 权限/枚举推导。
[ ] 控制命令：指示灯开关、WiFi 频段 2 项未实测。
[ ] **status.status 的语义**：0=匹配中 / 100=匹配成功 / 200=匹配失败。
    从措辞看这是"红外码库配对"的过程态，而非设备运行状态。
    装机后请确认它在配网/配对完成后是否稳定停在"匹配成功"。
[ ] WiFi 频段（netInfo.band）是否允许运行时切换未验证；
    部分机型该字段只在配网时生效，运行时写入可能被忽略。
[ ] 本适配器**不暴露任何被控家电的控制**（见上方两节说明）。
    如果你的实际需求是"用 HA 控制电视/空调"，需要的是另一套方案
    （在 App 内配置后用场景触发，或扩展 event 实体接收发码回执），
    请告知，我可以据此调整。
[ ] netInfo 各字段设备是否实际上报未验证（诊断类，不影响主功能）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .api import EntitySpec
from .context import DeviceContext

# netInfo.intensity：Profile 把信号格数编码为 20/40/60/80/100。
_SIGNAL_LEVELS = {20: 0, 40: 1, 60: 2, 80: 3, 100: 4}


# ---------------------------------------------------------------------
# 取值解码
# ---------------------------------------------------------------------
def _bool(value: Any) -> bool | None:
    """Decode a Huawei bool/enum characteristic into a Python bool."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().casefold() in {"1", "true", "on"}:
            return True
        if value.strip().casefold() in {"0", "false", "off"}:
            return False
        return None
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
    """Return one Profile characteristic definition, if declared.

    注意：本机 batchCmd 服务里 ``enable`` 这个字段名出现了两次
    （一个只读 enum、一个可写 int）。本函数只返回**第一个**匹配项，
    这也是该服务不被映射的原因之一（见文件头说明）。
    """

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
    """按 Profile 声明的 characteristicType 数值化命令取值。"""

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
    """只按 enumVal 精确匹配，不做 descCh/descEn 文本回退。

    本机 TVKey / STBKey / projectorKey 的枚举文案高度重复
    （都有"返回/菜单/信号源"等），文本匹配会命中错误档位。
    """

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
    return _coerce(raw, field)


def _enum_options(
    field: Mapping[str, Any] | None,
    order: tuple[str, ...] | None = None,
) -> tuple[tuple[Any, str], ...]:
    options: list[tuple[Any, str]] = []
    if not isinstance(field, Mapping):
        return ()
    for option in field.get("enumList", ()):
        if not isinstance(option, Mapping):
            continue
        raw = option.get("enumVal")
        if raw is None:
            continue
        label = option.get("descCh") or option.get("descEn") or str(raw)
        options.append((raw, str(label)))
    if order is not None:
        rank = {str(value): index for index, value in enumerate(order)}
        options.sort(key=lambda item: rank.get(str(item[0]), len(rank)))
    return tuple(options)


def _enum_label(field: Mapping[str, Any] | None, value: Any) -> str | None:
    if not isinstance(field, Mapping) or value is None:
        return None
    for option in field.get("enumList", ()):
        if not isinstance(option, Mapping):
            continue
        if str(option.get("enumVal")) != str(value):
            continue
        label = option.get("descCh") or option.get("descEn")
        if isinstance(label, str) and label.strip():
            return label.strip()
    return None


# ---------------------------------------------------------------------
# 实体构造
# ---------------------------------------------------------------------
def _make_switch(
    context: DeviceContext,
    sid: str,
    key: str,
    name: str,
) -> EntitySpec | None:
    """只用于**设备自身有真实回读**的布尔开关。"""

    field = _field(context.profile, sid, "on")
    if field is None or not _is_writable(field):
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


def _make_select(
    context: DeviceContext,
    sid: str,
    field_name: str,
    key: str,
    name: str,
    order: tuple[str, ...] | None = None,
) -> EntitySpec | None:
    """只用于**设备自身有真实回读**的枚举配置。"""

    field = _field(context.profile, sid, field_name)
    if field is None or not _is_writable(field):
        return None
    options = _enum_options(field, order)
    if not options:
        return None
    labels = tuple(label for _, label in options)
    by_label = {label: raw for raw, label in options}
    by_raw = {str(raw): label for raw, label in options}

    def state(device: DeviceContext) -> Mapping[str, Any]:
        raw = device.value(sid, field_name)
        if raw is None:
            return {"current_option": None}
        return {"current_option": by_raw.get(str(_int(raw)))}

    async def select(device: DeviceContext, data: Mapping[str, Any]) -> None:
        wanted = str(data.get("option"))
        raw = by_label.get(wanted)
        if raw is None:
            raise ValueError(f"unsupported option for {sid}.{field_name}: {wanted}")
        await device.async_send_service(sid, {field_name: _coerce(raw, field)})

    return EntitySpec(
        platform="select",
        key=key,
        name=name,
        state=state,
        metadata={"options": labels},
        actions={"select_option": select},
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
    decoder = decode or (lambda value: _number(value))

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


class Product2MJDAdapter:
    """Keep all 2MJD entity and command choices in this file."""

    prod_id = "2MJD"

    def entities(self, context: DeviceContext) -> tuple[EntitySpec, ...]:
        profile = context.profile
        if profile is None:
            return ()

        entities: list[EntitySpec] = []

        # --- 设备自身开关（有真实回读） -------------------------------
        spec = _make_switch(context, "indicatorSwitch", "indicator", "指示灯")
        if spec is not None:
            entities.append(spec)

        # --- 配对/匹配状态（设备自身的状态） --------------------------
        if context.has_service("status"):
            status_field = _field(profile, "status", "status")

            def match_state(device: DeviceContext) -> Mapping[str, Any]:
                raw = _int(device.value("status", "status"))
                if raw is None:
                    return {"native_value": None}
                label = _enum_label(status_field, raw)
                return {
                    "native_value": label if label is not None else raw,
                    "extra_state_attributes": {"raw_status": raw},
                }

            entities.append(
                EntitySpec(
                    platform="sensor",
                    key="match_status",
                    name="配对状态",
                    state=match_state,
                )
            )

        # --- WiFi 频段（设备自身配置，有回读） ------------------------
        if context.has_service("netInfo"):
            band_spec = _make_select(
                context, "netInfo", "band", "wifi_band", "WiFi 频段",
                ("1", "2"),
            )
            if band_spec is not None:
                entities.append(band_spec)

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
                    unit="dBm", device_class="signal_strength",
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


ADAPTER = Product2MJDAdapter()
