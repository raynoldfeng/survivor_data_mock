import re
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict


def parse_log(file_path):
    snapshots = []
    current_resources = {}
    current_buildings = defaultdict(lambda: defaultdict(lambda: {'complete': 0, 'under_construction': 0}))
    timestamp = None
    in_snapshot = False
    in_resources = False
    in_buildings = False

    item_count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 解析时间戳
            time_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}', line)
            if time_match:
                timestamp = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')

            # 检测分隔符
            if "-------------------------------------------" in line:
                if in_snapshot:
                    item_count += 1
                    # 结束当前快照
                    snapshots.append({
                        'timestamp': timestamp,
                        'resources': dict(current_resources),
                        'buildings': dict(current_buildings)
                    })
                    in_snapshot = False
                    in_resources = False
                    in_buildings = False
                else:
                    # 开始新的快照
                    in_snapshot = True
                    current_resources = {}
                    current_buildings = defaultdict(lambda: defaultdict(lambda: {'complete': 0, 'under_construction': 0}))
                continue

            if in_snapshot:
                if "当前资源：" in line:
                    in_resources = True
                    in_buildings = False
                    continue
                elif "已探索的星球及建筑：" in line:
                    in_resources = False
                    in_buildings = True
                    continue

                if in_resources:
                    # 匹配资源数据
                    res_match = re.match(r'.* - INFO - (\S+): (\d+(?:\.\d+)?)', line)
                    if res_match:
                        name = res_match.group(1).strip()
                        value = float(res_match.group(2))
                        current_resources[name] = value

                if in_buildings and "建筑:" in line:
                    # 匹配建筑数据
                    building_match = re.search(r'建筑: (.+?), 等级:(\d+)(?:\((.*?)\))?', line)
                    if building_match:
                        name = building_match.group(1).strip()
                        level = int(building_match.group(2))
                        status = building_match.group(3)
                        current_buildings[name][level]['complete'] += 1
                        if status:
                            current_buildings[name][level]['under_construction'] += 1

    return snapshots


def generate_charts(snapshots):
    # 处理资源数据
    resources_data = []
    for snap in snapshots:
        row = {'timestamp': snap['timestamp']}
        row.update(snap['resources'])
        resources_data.append(row)

    df_res = pd.DataFrame(resources_data)

    # 直接使用原始时间戳，不再分片
    df_res.set_index('timestamp', inplace=True)

    # 生成完整的时间范围（3分钟粒度）
    full_time_range = pd.date_range(
        start=df_res.index.min(),
        end=df_res.index.max(),
        freq='3T'
    )

    # 重新索引并前向填充
    df_res = df_res.reindex(full_time_range).ffill().reset_index()
    df_res.rename(columns={'index': 'timestamp'}, inplace=True)

    # 生成资源图表（X轴为timestamp，Y轴为资源值）
    fig_res = go.Figure()
    for col in df_res.columns[1:]:  # 排除timestamp列
        fig_res.add_trace(go.Scatter(
            x=df_res['timestamp'],
            y=df_res[col],
            name=col,
            mode='lines+markers'
        ))

    fig_res.update_layout(
        title='资源变化曲线（3分钟粒度）',
        xaxis_title='时间',
        yaxis_title='数量',
        height=600
    )

    # 处理建筑数据
    buildings_data = []
    for snap in snapshots:
        row = {'timestamp': snap['timestamp']}
        for building, levels in snap['buildings'].items():
            for level, stats in levels.items():
                row[f'{building}_L{level}_complete'] = stats['complete']
                row[f'{building}_L{level}_under_construction'] = stats['under_construction']
        buildings_data.append(row)

    df_bld = pd.DataFrame(buildings_data)

    # 直接使用原始时间戳，不再分片
    df_bld.set_index('timestamp', inplace=True)

    # 重新索引并前向填充
    df_bld = df_bld.reindex(full_time_range).ffill().reset_index()
    df_bld.rename(columns={'index': 'timestamp'}, inplace=True)

    # 生成建筑图表（X轴为timestamp，Y轴为建筑值）
    fig_bld = go.Figure()
    building_level_names = set([col for col in df_bld.columns if '_complete' in col or '_under_construction' in col])
    for building_level in building_level_names:
        total = df_bld[building_level]
        fig_bld.add_trace(go.Bar(
            x=df_bld['timestamp'],
            y=total,
            name=building_level
        ))

    fig_bld.update_layout(
        title='建筑曲线（3分钟粒度）',
        xaxis_title='时间',
        yaxis_title='数量',
        height=600,
        barmode='stack'
    )
    df_res.to_csv('resources.csv', index=False)
    df_bld.to_csv('buildings.csv', index=False)
    
    return fig_res, fig_bld


if __name__ == "__main__":
    snapshots = parse_log('log.txt')
    fig_res, fig_bld = generate_charts(snapshots)
    fig_res.write_html('resources.html')
    fig_bld.write_html('buildings.html')
    