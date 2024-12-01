# Cost optimization script

Allows you to quickly analyze the usage of your (supported) AWS resources and provide
you with low-hanging-fruit suggestions to optimize the AWS cloud costs.

You can combine the parameters provided to a script choosing the region and services you would like to scan.

### Supported Services

- EC2
- EBS
- RDS (not all engines yet)

### Requirements

You need only Python 3.9+ with dependencies defined in the `requirements.txt` file

## Example

```bash
$ python3.11 ./main.py -r us-east-1,us-west-2,eu-west-1 -m ebs,ec2,rds -v

Running in EBS mode us-east-1
| id                    | created   | status   | attachment          |   size | type   | cost   | future cost   | saving   |
|-----------------------|-----------|----------|---------------------|--------|--------|--------|---------------|----------|
| vol-0281c1a7c2ac1280d | 07-11-24  | in-use   | i-012a4ff9fb9cfc9ef |     30 | gp2    | 3.0$   | 2.4$          | 0.6$     |
| vol-05803c708e1c8eecf | 21-04-20  | in-use   | i-09ad82a7e90ec95ad |     50 | gp2    | 5.0$   | 4.0$          | 1.0$     |
| vol-0628f594c1e8e2fd8 | 19-11-24  | in-use   | i-0b1ef8b4c90dad8c7 |      8 | gp2    | 0.8$   | 0.64$         | 0.16$    |

Running in EC2 mode us-east-1
Checking i-0b2f46febcec54f75
Checking i-0b282e068f600e92f
Checking i-08c29af0eb1e7e75b
Checking i-0e492c8b543d4000b
| id                  | os    | started   | monitoring   | current             | future x86                         | future arm                         | 30 days load                     |
|---------------------|-------|-----------|--------------|---------------------|------------------------------------|------------------------------------|----------------------------------|
| i-0b2f46febcec54f75 | Linux | 11/07/21  | disabled     | t2.micro 8.468$     | t3a.micro 6.862$ (save:1.61$)      | t4g.micro 6.132$ (save:2.34$)      | is stopped                       |
| i-0b282e068f600e92f | Linux | 02/10/24  | disabled     | m6i.large 70.08$    | m6a.large 63.072$ (save:7.01$)     | m6g.large 56.21$ (save:13.87$)     | is stopped                       |
| i-08c29af0eb1e7e75b | Linux | 11/21/24  | disabled     | t2.micro 8.468$     | t3a.micro 6.862$ (save:1.61$)      | t4g.micro 6.132$ (save:2.34$)      | AVG: 3.91, MAX: 4.37, MIN: 3.29  |
| i-0e492c8b543d4000b | Linux | 06/03/20  | enabled      | m5.large 70.08$     | m6a.large 63.072$ (save:7.01$)     | m6g.large 56.21$ (save:13.87$)     | AVG: 1.0, MAX: 1.37, MIN: 0.95   |

Running in RDS mode us-east-1
| ClusterId (crop 20)   | Writer   | InstanceId (crop 20)   | MultiAZ   | Engine       | Current             | Future                            | 30 days CPU load                   |   Connections |
|-----------------------|----------|------------------------|-----------|--------------|---------------------|-----------------------------------|------------------------------------|---------------|
| N/A                   | N/A      | xxxx-dashboard         | True      | mariadb      | db.t3.medium 99.28$ | db.t4g.medium 94.17$ (save:5.11$) | AVG: 3.2, MAX: 20.31, MIN: 2.62    |            26 |
| seclust-zcpdq5tsyqdu  | True     | seclust-0xeaks91cedl   | False     | aurora-mysql | 0.07/1ACU           | N/A                               | AVG: 28.67, MAX: 40.34, MIN: 28.02 |            12 |
| seclust-zcpdq5tsyqdu  | False    | seclust-gacdw3bpm7zl   | False     | aurora-mysql | 0.07/1ACU           | delete node (save:0.07/1ACU$)     | AVG: 23.75, MAX: 74.28, MIN: 23.27 |             0 |


Running in EBS mode us-west-2

Running in EC2 mode us-west-2

Running in RDS mode us-west-2

Running in EBS mode eu-west-1
| id                    | created   | status    | attachment          |   size | type   | cost   | future cost   | saving   |
|-----------------------|-----------|-----------|---------------------|--------|--------|--------|---------------|----------|
| vol-0bf878d1b335bb008 | 11-11-24  | available |                     |     70 | gp3    | 6.65$  |               | 6.65$    |
| vol-0e6bfd57810af3698 | 22-02-22  | in-use    | i-04700f010778ea7ba |    100 | gp3    | 9.5$   |               |          |
| vol-02a2538057badedb2 | 28-10-24  | in-use    | i-05f5d43519a27e1a8 |    150 | gp3    | 14.25$ |               |          |
| vol-063ba83c97c10539f | 07-04-22  | in-use    | i-0713cb5f4ea4a5345 |    150 | gp2    | 17.85$ | 14.25$        | 3.6$     |


Running in EC2 mode eu-west-1
Checking i-0e1dd243c1af2e9a0
Checking i-017df641ed73c1ee1
Checking i-00c98c63596afb7dc
Checking i-0a9b7d29dce1ae458
Checking i-05af8bea5bbf0a63f
Checking i-086ea81fc79ea6802
| id                  | os      | started   | monitoring   | current                | future x86                         | future arm                         | 30 days load                       |
|---------------------|-------  |-----------|--------------|------------------------|------------------------------------|------------------------------------|------------------------------------|
| i-0e1dd243c1af2e9a0 | Linux   | 11/07/21  | enabled      | c5.large 70.08$        | c6a.large 59.918$ (save:10.16$)    | c6g.large 53.29$ (save:16.79$)     | AVG: 1.39, MAX: 2.06, MIN: 1.01    |
| i-017df641ed73c1ee1 | Linux   | 11/07/21  | disabled     | t3.xlarge 133.152$     | t3a.xlarge 119.136$ (save:14.02$)  | t4g.xlarge 107.456$ (save:25.7$)   | AVG: 0.31, MAX: 0.45, MIN: 0.28    |
| i-00c98c63596afb7dc | Linux   | 11/07/21  | disabled     | t2.micro 8.468$        | t3a.micro 6.862$ (save:1.61$)      | t4g.micro 6.132$ (save:2.34$)      | AVG: 2.82, MAX: 3.84, MIN: 2.55    |
| i-0a9b7d29dce1ae458 | Linux   | 01/03/19  | disabled     | t3.large 60.736$       | t3a.large 54.896$ (save:5.84$)     | t4g.large 49.056$ (save:11.68$)    | is stopped                         |
| i-05af8bea5bbf0a63f | Windows | 07/05/22  | disabled     | m5.xlarge 302.22$      | m6a.xlarge 285.43$ (save:16.79$)   | no Graviton for Windows            | AVG: 6.27, MAX: 7.73, MIN: 4.54    |
| i-086ea81fc79ea6802 | Linux   | 03/01/22  | enabled      | m5.large 83.95$        | m6a.large 75.555$ (save:8.39$)     | m6g.large 67.16$ (save:16.79$)     | AVG: 5.86, MAX: 6.21, MIN: 5.58    |

Running in RDS mode eu-west-1
| ClusterId(crop 20)   | Writer   | InstanceId(crop 20)   | MultiAZ   | Engine            | Current               | Future                     | 30 days CPU load                   |   Connections |
|----------------------|----------|-----------------------|-----------|-------------------|---------------------- |----------------------------|------------------------------------|---------------|
| cluster-d3derwduxxxx | True     | xxxxxxfmu92ck0        | False     | aurora-mysql      | db.r6g.xlarge 457.71$ | N/A                        | AVG: 10.86, MAX: 74.82, MIN: 6.36  |           118 |
| cluster-d3derwduxxxx | False    | xxxxxx4zlslba7        | False     | aurora-mysql      | db.r6g.xlarge 457.71$ | delete node (save:457.71$) | AVG: 3.29, MAX: 4.31, MIN: 3.0     |             0 |
| y-postgresql-cluster | True     | xxx-postgresql        | False     | aurora-postgresql | db.t4g.large 148.19$  | N/A                        | AVG: 43.72, MAX: 80.93, MIN: 31.29 |           117 |

Running in EBS mode ap-southeast-2

Running in EC2 mode ap-southeast-2

Running in RDS mode ap-southeast-2
```
