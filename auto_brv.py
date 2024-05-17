import subprocess
import argparse
import xml.etree.ElementTree as ET
import os
import sys
# 设置build,run,verify的flag。如果不传递参数，默认依次进行build,run,verify，否则根据传入的参数进行组合
parser = argparse.ArgumentParser()
parser.add_argument('-b', '--build', action='store_true',
                    help='Set the build flag to True',default=False)
parser.add_argument('-r', '--run', action='store_true',
                    help='Set the run flag to True',default=False)
parser.add_argument('-v', '--verify', action='store_true',
                    help='Set the verify flag to True',default=False)
parser.add_argument('-c', '--cuda', action='store_true',
                    help='Set the cuda flag to True',default=False)
parser.add_argument('-m', '--maca', action='store_true',
                    help='Set the maca flag to True',default=False)
parser.add_argument('-l','--clean', action='store_true',
                    help='Set the clean flag to True',default=False)


args = parser.parse_args()

EXIT_PASS = 0
EXIT_FAILED = 1
failed_flag = False


CUDA = False
MACA = False
build_stage = False
run_stage = False
verify_stage = False
clean_stage =False

if not any(vars(args).values()):
    build_stage = True
    run_stage = True
    verify_stage = True
    clean_stage =True
    CUDA = True
    MACA = True
else:
    build_stage = args.build
    run_stage = args.run
    verify_stage = args.verify
    clean_stage = args.clean
    CUDA = args.cuda
    MACA = args.maca

print('CUDA:{}\nMACA:{}\nbuild:{}\nrun:{}\nverify:{}\nclean:{}'.format(CUDA,MACA,build_stage,run_stage,verify_stage,clean_stage))

global_root_path = os.getcwd()     # 获取脚本所在的根目录路径，用于后续的目录切换 
print(f'global_root_path:{global_root_path}')
cuda_root_path = os.path.join(global_root_path,'cuda')  # 这是CUDA项目的根目录
maca_root_path = os.path.join(global_root_path,'maca')  # 这是MACA项目的根目录

xml_name = 'info.xml'

work_root_paths = []        # 为了统一处理CUDA和MACA，二者的根目录统称为工作根目录

if CUDA:
    work_root_paths.append(cuda_root_path)
if MACA:
    work_root_paths.append(maca_root_path)
        

project_build_failed_num = 0    # failed一般情况下表示某个命令执行出错
project_build_pass_num = 0      # pass表示没有出现错误
project_build_error_num = 0     # error 表示出现了意料之外的一些错误

project_run_failed_num = 0
project_run_pass_num = 0
project_run_error_num = 0

project_verify_failed_num = 0
project_verify_pass_num = 0
project_verify_error_num = 0


tests_init_path_set = set()     # 每个test都有自己的目录，这个目录可能重复。在正式构建前需要进入对应目录进行一些初始化工作
tests_init_failed_list = []     # 初始化失败的目录存储在这个变量中。初始化失败的test不参与后续的构建。

tests_clean_path_set = set()     # 每个test都有自己的目录，这个目录可能重复。在正式构建前需要进入对应目录进行一些初始化工作


def clean():
    print('*****************CLEAN*****************')
    for work_root_path in work_root_paths:
        # 进入工作根目录，后面要切换会回根目录都是到这个目录
        os.chdir(work_root_path)
        print(f'work_root_path:{work_root_path}')
        flag = work_root_path[-4:]
        print('*****************{}*****************'.format(flag.upper()))
        # xml_path = os.path.join(work_root_path,xml_name)
        # 解析xml文件
        tree = ET.parse(xml_name)
        root = tree.getroot()
        project_tests = root.find('Tests')
        for test in project_tests.iter('Test'):
            test_name = test.find('Name').text
            test_path = test.find('Path').text
            test_bug = test.find('Bug')
            test_build_status = test.find('Build').text
            # if test_build_status == 'pass':
            #     tests_clean_path_set.add(test_path)
            tests_clean_path_set.add(test_path)
            # 依次进行clean
        for path in tests_clean_path_set:
            # 首先判断目录是否存在
            if not os.path.exists(path):
                print('clean error:{} not exists'.format(path))
                failed_flag =  True
            else:
                os.chdir(path)
                if not os.path.exists('./build.py'):
                    print('clean error:{} is not exists'.format(os.path.join(path,'build.py')))
                    failed_flag =  True
                else:
                    # 用参数：init作为初始化操作的参数
                    code,output = subprocess.getstatusoutput('python ./build.py -n clean')
                    if code==255:
                        # 初始化失败，一般是命令执行出错，打印错误信息
                        print('clean failed:{}\n{}'.format(path,output))
                        failed_flag =  True
                    elif code == 0:
                        # clean成功
                        print('clean pass:{}'.format(path))
                    else:
                        # clean失败，且发生了意料之外的错误
                        print('clean error:{}\nerror code:{}\n{}'.format(path,code,output))
                        failed_flag =  True
                    # 回到根目录，初始化下一个目录
                os.chdir(work_root_path)
    print('*****************END*****************')
# 如果只需要clean
if clean_stage and not build_stage and not run_stage and not verify_stage:
    clean()
    # sys.exit(0)
# 否则要走流程
else:
    # 使用循环来处理CUDA和MACA项目
    for work_root_path in work_root_paths:
        # 根据工作根目录来判断当前是在处理CUDA还是MACA项目
        if work_root_path == cuda_root_path:
            print('*****************CUDA*****************')
        elif work_root_path == maca_root_path:
            print('*****************MACA*****************')
        # 进入工作根目录，后面要切换会回根目录都是到这个目录
        os.chdir(work_root_path)
        # xml_path = os.path.join(work_root_path,xml_name)
        # 解析xml文件
        tree = ET.parse(xml_name)
        root = tree.getroot()

        # xml中这些变量的值需要根据构建的结果来确定
        project_build_status = root.find('Project_Status/Build_Status')
        project_run_status = root.find('Project_Status/Run_Status')
        project_verify_status = root.find('Project_Status/Verify_Status')
        # 获取所有的test元素
        project_tests = root.find('Tests')
        if build_stage:
            # 下面开始对xml中所有的test进行构建前的初始化
            # 获取所有test的的目录，放入set去重复
            for test in project_tests.iter('Test'):
                test_path = test.find('Path').text
                tests_init_path_set.add(test_path)

            # 依次进行构建前的初始化
            for path in tests_init_path_set:
                # 首先判断目录是否存在
                if not os.path.exists(path):
                    print('build init error:{} not exists'.format(path))
                    tests_init_failed_list.append(path)
                else:
                    os.chdir(path)
                    if not os.path.exists('./build.py'):
                        print('build init error:{} is not exists'.format(os.path.join(path,'build.py')))
                        tests_init_failed_list.append(path)
                    else:
                        # 用参数：init作为初始化操作的参数
                        code,output = subprocess.getstatusoutput('python ./build.py -n init')
                        if code==255:
                            # 初始化失败，一般是命令执行出错，打印错误信息
                            print('build init failed:{}\n{}'.format(path,output))
                            tests_init_failed_list.append(path)
                        elif code == 0:
                            # 初始化成功
                            print('build init pass:{}'.format(path))
                        else:
                            # 初始化失败，且发生了意料之外的错误
                            print('build init error:{}\nerror code:{}\n{}'.format(path,code,output))
                            tests_init_failed_list.append(path)
                        # 回到根目录，初始化下一个目录
                    os.chdir(work_root_path)

            # 对初始化成功的所有test进行build
            for test in project_tests.iter('Test'):
                test_name = test.find('Name').text
                test_path = test.find('Path').text
                test_bug = test.find('Bug')
                test_build_status = test.find('Build')
                if not test_path in tests_init_failed_list:
                    # 读取test的基本信息后进入其所在的目录，调用该目录下的build.py，该脚本接受test的name作为参数
                    os.chdir(test_path)
                    code,output = subprocess.getstatusoutput('python ./build.py -n {}'.format(test_name))
                    # 将test的目录与名字连接在一起，方便出错后判断
                    test_path_name = os.path.join(test_path,test_name)
                    # 如果执行build.py后得到的返回值为：255，说明由于某些原因导致test构建失败
                    if code == 255:
                        # 增加project的build失败的计数
                        project_build_failed_num = project_build_failed_num + 1
                        # 将当前test的build状态修改为failed
                        test_build_status.text = 'failed'
                        # 打印编译失败的test的name
                        print('build failed:{}'.format(test_path_name))
                        # 打印编译失败后得到的输出（这个输出是在build.py进行打印，在这里则是作为返回值来打印）
                        print(output)     
                        test_bug.text = 'build failed:{}\n{}'.format(test_path_name,output)
                    elif code==254:
                        # 如果执行build.py后得到的返回值为：254，说明需要构建的test不在目录下（test的path或name中有一个或都出错）
                        project_build_error_num = project_build_error_num + 1
                        print('build error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd()))
                        test_bug.text = 'build error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd())
                    elif code == 0:
                        # 如果执行build.py后得到的返回值为：0，说明test构建成功
                        project_build_pass_num = project_build_pass_num + 1
                        test_build_status.text='pass'
                        print('build pass:{}'.format(test_path_name))
                        test_bug.text = ''
                    else:
                        project_build_error_num = project_build_error_num + 1
                        # 产生了其他错误，将返回码、脚本执行时所在的路径、错误信息都打印出来
                        print('build error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output))
                        test_bug.text = 'build error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output)
                    # 回到根目录，如果没有回到根目录，会影响test的遍历
                    os.chdir(work_root_path)
                else:
                    # 没有参与build的test也需要修改状态
                    test_build_status.text = 'failed'
                    test_bug.text = 'build init error'
            # 所有的test都经过build，将统计信息写入xml，并打印统计信息
            project_build_status.find('Failed').text = str(project_build_failed_num+project_run_error_num)
            project_build_status.find('Pass').text = str(project_build_pass_num)
            print('total build pass:{}\ntotal build failed:{}\ntotal build error:{}'.format(project_build_pass_num,project_build_failed_num,project_build_error_num))
            if project_build_failed_num >0 or project_build_error_num>0:
                failed_flag = True
        if run_stage:
            # 对符合条件的test进行run
            for test in project_tests.iter('Test'):
                test_name = test.find('Name').text
                test_path = test.find('Path').text
                test_bug = test.find('Bug')
                test_build_status = test.find('Build')
                test_run_status = test.find('Run')
                # 运行build成功的test
                if test_build_status.text == 'pass':
                # 读取test的基本信息后进入其所在的目录，调用该目录下的build.py，该脚本接受test的name作为参数
                    os.chdir(test_path)
                    if not os.path.exists('./run.py'):
                        print('run error:{} is not exists'.format(os.path.join(test_path,'run.py')))
                        project_run_error_num = project_run_error_num + 1
                    else:
                        code,output = subprocess.getstatusoutput('python ./run.py -n {}'.format(test_name))
                        # 如果执行build.py后得到的返回值为：255，说明由于某些原因导致test构建失败
                        test_path_name = os.path.join(test_path,test_name)
                        if code == 255:
                            # 增加project的build失败的计数
                            project_run_failed_num = project_run_failed_num + 1
                            # 将当前test的build状态修改为failed
                            test_run_status.text = 'failed'
                            # 打印编译失败的test的name
                            print('run failed:{}'.format(test_path_name))
                            # 打印编译失败后得到的输出（这个输出是在build.py进行打印，在这里则是作为返回值来打印）
                            print(output)
                            test_bug.text = 'run failed:{}\n{}'.format(test_path_name,output)
                        elif code==254:
                            project_run_error_num = project_run_error_num + 1
                            # 如果执行build.py后得到的返回值为：254，说明需要构建的test不在目录下（test的path或name中有一个或都出错）
                            print('run error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd()))
                            test_bug.text = 'run error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd())
                        elif code == 0:
                            # 如果执行build.py后得到的返回值为：0，说明test构建成功
                            project_run_pass_num = project_run_pass_num + 1
                            test_run_status.text='pass'
                            print('run pass:{}'.format(test_path_name))
                            test_bug.text = ''
                        else:
                            project_run_error_num = project_run_error_num + 1
                            # 产生了其他错误，将返回码、脚本执行时所在的路径、错误信息都打印出来
                            print('run error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output))
                            test_bug.text = 'run error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output)
                    # 回到根目录，如果没有回到根目录，会影响test的遍历
                    os.chdir(work_root_path)
                else:
                    # 这里不用写bug，因为对应的test在build阶段已经失败并写了bug
                    test_run_status.text = 'failed'

            project_run_status.find('Failed').text = str(project_run_failed_num+project_run_error_num)
            project_run_status.find('Pass').text = str(project_run_pass_num)
            print('total run pass:{}\ntotal run failed:{}\ntotal run error:{}'.format(project_run_pass_num,project_run_failed_num, project_run_error_num))
            if project_run_failed_num >0 or project_run_error_num>0:
               failed_flag = True
        # 只有进行MACA构建的时候才进行verify
        if verify_stage and work_root_path == maca_root_path:
            for test in project_tests.iter('Test'):
                test_name = test.find('Name').text
                test_path = test.find('Path').text
                test_bug = test.find('Bug')
                test_build_status = test.find('Build')
                test_run_status = test.find('Run')
                test_verify_status = test.find('Verify')
                # 运行build成功的test
                if test_run_status.text == 'pass':
                # 读取test的基本信息后进入其所在的目录，调用该目录下的build.py，该脚本接受test的name作为参数
                    os.chdir(test_path)
                    if not os.path.exists('./verify.py'):
                        print('verify error:{} is not exists'.format(os.path.join(test_path,'verify.py')))
                        project_verify_error_num = project_verify_error_num + 1
                    else:
                        code,output = subprocess.getstatusoutput('python ./verify.py -n {}'.format(test_name))
                        # 如果执行verify.py后得到的返回值为：255，说明由于某些原因导致test验证失败
                        test_path_name = os.path.join(test_path,test_name)
                        if code == 255:
                            # 增加project的verify失败的计数
                            project_verify_failed_num = project_verify_failed_num + 1
                            # 将当前test的verify状态修改为failed
                            test_verify_status.text = 'failed'
                            # 打印编译失败的test的name
                            print('verify failed:{}'.format(test_path_name))
                            # 打印编译失败后得到的输出（这个输出是在build.py进行打印，在这里则是作为返回值来打印）
                            print(output)
                            test_bug.text = 'verify failed:{}\n{}'.format(test_path_name,output)
                        elif code==254:
                            project_verify_error_num = project_verify_error_num + 1
                            # 如果执行build.py后得到的返回值为：254，说明需要构建的test不在目录下（test的path或name中有一个或都出错）
                            print('verify error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd()))
                            test_bug.text = 'verify error: can\'t find test:{}\npath:{}'.format(test_path_name,os.getcwd())
                        elif code==253:
                            # 验证过程中存在路径错误
                            project_verify_error_num = project_verify_error_num + 1
                            print(output)
                            test_bug.text = output
                        elif code == 0:
                            # 如果执行verify.py后得到的返回值为：0，说明test验证成功
                            project_verify_pass_num = project_verify_pass_num + 1
                            test_verify_status.text='pass'
                            print('verify pass:{}'.format(test_path_name))
                            test_bug.text = ''
                        else:
                            project_verify_error_num = project_verify_error_num + 1
                            # 产生了其他错误，将返回码、脚本执行时所在的路径、错误信息都打印出来
                            print('verify error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output))
                            test_bug.text = 'verify error code:{}\npath:{}\n{}'.format(code,os.getcwd(),output)
                    # 回到根目录，如果没有回到根目录，会影响test的遍历
                    os.chdir(work_root_path)
                else:
                    # 这里不用写bug，因为对应的test在build阶段已经失败并写了bug
                    test_verify_status.text = 'failed'

            project_verify_status.find('Failed').text = str(project_verify_failed_num+project_verify_error_num)
            project_verify_status.find('Pass').text = str(project_verify_pass_num)
            print('total verify pass:{}\ntotal verify failed:{}\ntotal verify error:{}'.format(project_verify_pass_num,project_verify_failed_num, project_verify_error_num))
            if project_verify_failed_num >0 or project_verify_error_num>0:
                failed_flag = True
        # cuda无需执行verify，因此将cuda对应的xml中的verify数量置为0
        elif verify_stage and work_root_path == cuda_root_path:
            project_verify_status.find('Failed').text = str(0)
            project_verify_status.find('Pass').text = str(0)
        # 在此之前，xml只是被解析到了内存中，所有的修改也都在内存中，现在将它写入文件
        tree.write(xml_name)

        project_build_failed_num = 0    # failed一般情况下表示某个命令执行出错
        project_build_pass_num = 0      # pass表示没有出现错误
        project_build_error_num = 0     # error 表示出现了意料之外的一些错误

        project_run_failed_num = 0
        project_run_pass_num = 0
        project_run_error_num = 0

        project_verify_failed_num = 0
        project_verify_pass_num = 0
        project_verify_error_num = 0
    
        print('*****************END*****************')
    # 最后对中间文件进行清理，使用的是build.py脚本，需要传递的参数是 -n clean
    if clean_stage:
       clean()
    if failed_flag:
        sys.exit(EXIT_FAILED)
    else:
        sys.exit(EXIT_PASS)