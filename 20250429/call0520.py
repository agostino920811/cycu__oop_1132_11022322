import bus0520

if __name__ == '__main__':
    # 提供多個 bus_id，使用逗號分隔
    bus_ids = "0161001500, 0161000900"
    
    # 將 bus_ids 分割成列表
    bus_id_list = [bus_id.strip() for bus_id in bus_ids.split(",")]
    
    # 逐一處理每個 bus_id
    for bus_id in bus_id_list:
        print(f"正在處理公車路線 {bus_id} 的資訊...")
        bus_info_11022143.bus_info(bus_id)