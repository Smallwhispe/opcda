# 路由处理函数
@app.route('/workpiece/get', methods=['GET'])
# 定义一个路由处理函数，并将其与URL规则`/linklist`关联起来。这个路由将响应HTTP GET请求。
def get():
    # 定义一个函数，用于处理对`/linklist`路由的GET请求。
    links = OutputGongJianBiao.query.all()
    print(links)
    # 将查询结果转换为字典列表
    data = {'list':[{'orderid': link.orderid, 'workpieceid': link.workpieceid, 'number': link.number, 'workpieceinformation': link.workpieceinformation} for link in links]}
    # 返回JSON响应
    return jsonify(data)
    # 使用`jsonify`函数将字典列表转换为JSON格式的响应体，并返回给客户端。

@app.route('/workpiece/save', methods=['POST'])
def save():
    data = request.json
    new_item = OutputGongJianBiao(orderid=data['orderid'],workpieceid=data['workpieceid'],number=data['number'],workpieceinformation=data['workpieceinformation'])
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'orderid': new_item.orderid, 'number':new_item.number}), 200

@app.route('/workpiece/search', methods=['POST'])
def search():
    data = request.json
    query = OutputGongJianBiao.query  # 开始一个查询

    # 动态添加过滤条件
    if data.get('orderid') is not None and data['orderid'] != '':
        query = query.filter(OutputGongJianBiao.orderid == data['orderid'])
    if data.get('workpieceid') is not None and data['workpieceid'] != '':
        query = query.filter(OutputGongJianBiao.workpieceid == data['workpieceid'])
    if data.get('number') is not None and data['number'] != '':
        query = query.filter(OutputGongJianBiao.number == data['number'])
    if data.get('workpieceinformation') is not None and data['workpieceinformation'] != '':
        query = query.filter(OutputGongJianBiao.workpieceinformation == data['workpieceinformation'])

    links = query.all()  # 获取所有匹配的条目

    # 转换为字典格式以便返回
    results = {'list':[{'orderid': link.orderid, 'workpieceid': link.workpieceid, 'number': link.number, 'workpieceinformation': link.workpieceinformation} for link in links]}
    return jsonify(results), 200  # 返回所有匹配的条目

@app.route('/workpiece/delete', methods=['POST'])
def delete():
    data = request.json
    new_item = OutputGongJianBiao.query.get_or_404(data['orderid'])
    db.session.delete(new_item)
    db.session.commit()
    return jsonify({'orderid': new_item.orderid, 'number':new_item.number}), 200