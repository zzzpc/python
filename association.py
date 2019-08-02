# coding: utf-8
import itertools
import pymysql

Minsupportpct=5
allSingletonTags=[]
allDoubletonTags=set()
doubletonSet=set()
db= pymysql.connect(
    host='localhost',
    db='test',
    user='root',
    passwd='123456',
    port=3306,
    charset='utf8mb4')
cursor=db.cursor()
queryBaskets="select count(distinct project_id) from fc_project_tags;"
cursor.execute(queryBaskets)
baskets = cursor.fetchone()[0]
print('共发现项目：{}项'.format(baskets))
minsupport = baskets*(Minsupportpct/100)
print("设置阈值为：{} 项,即认为支持度阈值为5%".format(minsupport))
#选择大于最小支持度的项并且以字母降序返回
cursor.execute("select distinct tag_name, count(project_id) from fc_project_tags group by 1 having count(project_id) >=  %s  order by tag_name desc",(minsupport))
singletons=cursor.fetchall()
print(len(singletons))

for (singleton) in singletons:
    allSingletonTags.append(singleton[0])
print('由此得到所有符合5%支持阈值的项目:')
print(singletons)


#定义相关函数
#双项目关联函数
def findDoubletons():
    print('由此得到所有符合支持阈值的有两个内容的项目数')
    doubletonCandidates = list(itertools.combinations(allSingletonTags,2))#从29个中任意选2个项集(C2,29)最后存到list中
    num = 0
    for(index,candidate) in enumerate(doubletonCandidates):  #枚举doubletonCandidates中的元素

        tag1 = candidate[0]  #候选集0
        tag2 = candidate[1]  #候选集1
        cursor.execute(
            "select count(fpt1.project_id) from fc_project_tags fpt1 inner join fc_project_tags fpt2  on fpt1.project_id = fpt2.project_id    where fpt1.tag_name = %s  and fpt2.tag_name = %s ",
            (tag1, tag2))
        count = cursor.fetchone()[0]
        if count > minsupport:

            #print(tag1, ',', tag2, "[", count, "]")
            cursor.execute("insert into fc_project_tag_pairs (tag1, tag2, num_projs) values (%s,%s,%s)",(tag1, tag2, count))
            print("成功插入：{}条数据".format(num))
            num+=1
            doubletonSet.add(candidate)
            allDoubletonTags.add(tag1)
            allDoubletonTags.add(tag2)
    cursor.execute(
        "select count(*) from fc_project_tag_pairs ")
    testnum= cursor.fetchone()[0]
    return  doubletonSet,testnum

findDoubletons()

#关联三元组生成
def findTripletons():
    print("三元组如下：")
    tripletonCandidates = list(itertools.combinations(allDoubletonTags,3))
    tripletonCandidatesSorted=[]
    for tc in tripletonCandidates:
        tripletonCandidatesSorted.append(sorted(tc))
    for (index,candidate) in enumerate(tripletonCandidatesSorted):
        doubletonsInsideTripleton=list(itertools.combinations(candidate,2))
        tripletonCandidateRejected = 0
        for (index,doubleton) in enumerate(doubletonsInsideTripleton):
            if doubleton not in doubletonSet and doubleton[::-1] not in doubletonSet:
                tripletonCandidateRejected = 1
                break
        if tripletonCandidateRejected == 0:
            cursor.execute("select count(fpt1.project_id) from fc_project_tags fpt1             inner join fc_project_tags fpt2             on fpt1.project_id=fpt2.project_id             inner join fc_project_tags fpt3             on fpt2.project_id=fpt3.project_id             where (fpt1.tag_name= %s and fpt2.tag_name= %s and fpt3.tag_name =%s)",
                           (candidate[0],candidate[1],candidate[2]))
            count = cursor.fetchone()[0]
            if count > minsupport:
                print(candidate[0],",",candidate[1],",",candidate[2],"[",count,"]")
                cursor.execute("insert into fc_project_tag_triple                 (tag1, tag2, tag3, num_projs) values (%s,%s,%s,%s)",(candidate[0],candidate[1],candidate[2],count))

findTripletons()


def calcSCAV(tagA, tagB, tagC, ruleSupport):
    ruleSupportPct = round((ruleSupport / baskets), 2)#按指定的位数进行四舍五入 ， 2为指定的位数
    query1 = "select num_projs     from fc_project_tag_pairs     where (tag1 = %s and tag2 = %s)     or (tag1 = %s and tag2 = %s)"
    cursor.execute(query1, (tagA, tagB, tagB, tagA))
    pairSupport = cursor.fetchone()[0]
    confidence = round((ruleSupport / pairSupport), 2)
    query2 = "select count(*)     from fc_project_tags     where tag_name=%s"
    cursor.execute(query2, tagC)
    supportTagC = cursor.fetchone()[0]
    supportTagCPct = supportTagC / baskets
    addedValue = round((confidence - supportTagCPct), 2)
    print(tagA, ",", tagB, "-->", tagC, "S=[", ruleSupportPct, "]", "C=[", confidence, "]", "AV=[", addedValue, "]",)


def generateRules():
    cursor.execute("select tag1,tag2,tag3,num_projs from fc_project_tag_triple")
    triples = cursor.fetchall()
    for (triple) in triples:
        tag1 = triple[0]
        tag2 = triple[1]
        tag3 = triple[2]
        ruleSupport = triple[3]
        calcSCAV(tag1, tag2, tag3, ruleSupport)
        calcSCAV(tag1, tag3, tag2, ruleSupport)
        calcSCAV(tag2, tag3, tag1, ruleSupport)

generateRules()
