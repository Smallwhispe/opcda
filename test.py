import OpenOPC

# --- 配置 ---
GATEWAY_HOST = '192.168.57.227'
OPC_SERVER_NAME = 'HWHsc.OPCServer'

# 定义要读取的 Tag 列表
tags = [
    'TI1352A.DACA.PV',
    'TI1329.DACA.PV',
    'TI1328.DACA.PV',
    'PIC1306.PIDA.PV',
    'TI1338.DACA.PV',
    'FIC1308.PIDA.PV',
    'FIC1309.PIDA.PV',
    'FIC1310.PIDA.PV',
    'FIC1303.PIDA.PV',
    'FIC1311.PIDA.PV',
    'TI1330.DACA.PV',
    'TIC1201B.PIDA.PV',
    'PI1204.DACA.PV',
    'FIC1214.PIDA.PV',
    'FI1160.DACA.PV',
    'FIC1210.PIDA.PV',
    'FIC1203.PIDA.PV',
    'FI1405.DACA.PV',
    'FI1314.DACA.PV',
    'FI1312.DACA.PV',
    'PI1308.DACA.PV',
    'TI1304.DACA.PV',
    'TIC1345.PIDA.PV',
    'FIC1307.PIDA.PV',
    'FIC1306.PIDA.PV',
    'FIC1305.PIDA.PV',
    'FIC1304.PIDA.PV',
    'PI1304.DACA.PV',
    'TI1308.DACA.PV',
    'TI1310.DACA.PV',
    'TI1312.DACA.PV',
    'TI1314.DACA.PV',
    'TI1341.DACA.PV',
    'TI1347.DACA.PV',
    'TIC1101.PIDA.PV',
    'TIC1103.PIDA.PV',
    'TI1233C.PIDA.PV',
    'TI1306.DACA.PV'
]

print(f"1. 正在连接网关: {GATEWAY_HOST}...")

try:
    # 1. 连接到 OpenOPC 网关
    client = OpenOPC.open_client(GATEWAY_HOST)

    print(f"2. 正在连接 OPC 服务器: {OPC_SERVER_NAME}...")

    # 2. 连接到具体的 OPC Server
    client.connect(OPC_SERVER_NAME)

    print("3. 开始检查点位有效性...")

    # 检查每个点位是否存在
    valid_tags = []
    invalid_tags = []

    for tag in tags:
        try:
            # 尝试读取单个点位来检查是否存在
            result = client.read(tag)
            print(result)
            if result:
                value, quality, timestamp = result
                if quality == 'Good':  # 质量好表示点位有效
                    valid_tags.append(tag)
                    print(f"✓ 点位有效: {tag}")
                else:
                    invalid_tags.append(tag)
                    print(f"✗ 点位无效(质量差): {tag} - 质量: {quality}")
            else:
                invalid_tags.append(tag)
                print(f"✗ 点位无效(无数据): {tag}")

        except Exception as e:
            invalid_tags.append(tag)
            print(f"✗ 点位读取错误: {tag} - 错误: {e}")

    print(f"\n点位检查完成:")
    print(f"有效点位: {len(valid_tags)} 个")
    print(f"无效点位: {len(invalid_tags)} 个")

    if invalid_tags:
        print(f"\n无效点位列表:")
        for tag in invalid_tags:
            print(f"  - {tag}")

    if valid_tags:
        print(f"\n4. 开始读取有效点位数据...")

        # 批量读取有效点位
        data_list = client.read(valid_tags)

        print("\n" + "=" * 60)
        if data_list:
            print(f"成功读取 {len(data_list)} 个点位的数据:")
            print("=" * 60)

            for i, item in enumerate(data_list, 1):
                try:
                    # 解包元组
                    tag_name, value, quality, timestamp = item
                    print(f"{i:2d}. {tag_name}")
                    print(f"    数值   : {value}")
                    print(f"    质量   : {quality}")
                    print(f"    时间   : {timestamp}")
                    print("-" * 50)
                except Exception as e:
                    print(f"{i:2d}. 数据解析错误: {item} - 错误: {e}")
                    print("-" * 50)
        else:
            print("读取结果为空！")
        print("=" * 60)

        # 打印原始数据列表
        print(f"\n原始数据列表:")
        print(str(data_list))
    else:
        print("没有有效点位可读取！")

    # 5. 关闭连接
    client.close()
    print("\n连接已关闭。")

except Exception as e:
    print(f"\n发生错误: {e}")
    # 尝试在出错时关闭连接（如果 client 存在）
    try:
        if 'client' in locals():
            client.close()
    except:
        pass