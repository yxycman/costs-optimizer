# Cost optimization script

Allows you to quickly analyze the usage of your (supported) AWS resources and provide
you with low-hanging-fruit suggestions to optimize the AWS cloud costs.

You can combine the parameters provided to a script choosing the region and services you would like to scan.

### Supported Services

- EC2
- EBS
- RDS (not all engines yet)

### Requirements

You need only Python 3.11+ with dependencies defined in the `requirements.txt` file

## Example

```bash
$ python3.12 main.py -r eu-central-1 -e ~/Downloads/test-export.xlsx -m ami,ecr,ebs,ec2,rds,lb

✨  Running in ECR Images mode eu-central-1 for images not used within 90 days


✨  Running in EBS volume mode eu-central-1
|| VolumeId              | Created    | Status    | Attachment          |   Size | Type   |   Cost |   Future cost |   Saving |
|-----------------------|------------|-----------|---------------------|--------|--------|--------|---------------|----------|
| vol-xxxxxxxxxxxxxxxxx | 2025-05-13 | available |                     |    500 | gp3    |  40.00 |               |    40.00 |
| vol-xxxxxxxxxxxxxxxxx | 2024-06-03 | in-use    | i-xxxxxxxxxxxxxxxxx |    500 | gp3    |  40.00 |               |          |
| vol-xxxxxxxxxxxxxxxxx | 2025-03-05 | in-use    | i-xxxxxxxxxxxxxxxxx |     32 | gp2    |   3.20 |          2.56 |     0.64 |


✨  Running in EBS snapshot mode eu-central-1
| SnapshotId             | Description (crop 100)                                                |   Volume size |   Snapshot size * | State     | Start time   | Tier     |   Cost/GB |   Cost/Month |
|------------------------|-----------------------------------------------------------------------|---------------|-------------------|-----------|--------------|----------|-----------|--------------|
| snap-xxxxxxxxxxxxxxxxx | Created for ami-xxxxxxxxxxxxxxxxx |           500 |               500 | completed | 2025-08-01   | standard |      0.05 |        27.00 |


✨  Running in EC2 instance mode eu-central-1
Processing i-xxxxxxxxxxxxxxxxx
Processing i-xxxxxxxxxxxxxxxxx
Processing i-xxxxxxxxxxxxxxxxx
Processing i-xxxxxxxxxxxxxxxxx
Processing i-xxxxxxxxxxxxxxxxx
Processing i-xxxxxxxxxxxxxxxxx
| InstanceId          | Name (crop 20)     | OS      | Started    | Monitoring   | Current             | Future x86                       | Future arm                       | 30 days load                       |
|---------------------|--------------------|---------|------------|--------------|---------------------|----------------------------------|----------------------------------|------------------------------------|
| i-xxxxxxxxxxxxxxxxx | testtesttesttest   | Linux   | 2025-01-31 | disabled     | t2.micro 9.782      | t3a.micro 7.884 (save:1.9)       | t4g.micro 7.008 (save:2.77)      | stopped: ['2025-03-24']            |
| i-xxxxxxxxxxxxxxxxx | testtesttesttest   | Windows | 2025-02-27 | disabled     | r7i.2xlarge 734.672 | r6a.2xlarge 668.096 (save:66.58) | no Graviton for Windows          | AVG: 4.97, MAX: 11.27, MIN: 4.1    |
| i-xxxxxxxxxxxxxxxxx | testtesttesttest   | Linux   | 2025-07-31 | disabled     | t3.2xlarge 280.32   | t3a.2xlarge 252.288 (save:28.03) | t4g.2xlarge 224.256 (save:56.06) | AVG: 5.84, MAX: 11.68, MIN: 4.33   |


✨  Running in RDS mode eu-central-1
| ClusterId (crop 20)   | Writer   | InstanceId (crop 20)   | MultiAZ   | Engine            |   Engine Version | Current              | Future   | 30 days CPU load                  |   Connections |
|-----------------------|----------|------------------------|-----------|-------------------|------------------|----------------------|----------|-----------------------------------|---------------|
|  testtesttesttest     | True     | testtesttesttest       | False     | aurora-postgresql |            16.60 | db.r8g.xlarge 632.18 | N/A      | AVG: 12.89, MAX: 15.86, MIN: 8.09 |            99 |


✨  Running in Load Balancer V1 mode eu-central-1
✨  Running in Load Balancer V2 mode eu-central-1
| LoadBalancerId                                        | Name (crop 20)                   | Type        | 30 days RequestCount/ActiveConnectionCount   |   Monthly hour cost |
|-------------------------------------------------------|----------------------------------|-------------|----------------------------------------------|---------------------|
| a3b4383563ec14403b29cabdb1c8bc5f                      | a3b4383563ec14403b29cabdb1c8bc5f | classic     | AVG: 0, MAX: 0, MIN: 0                       |               18.25 |
| app/xxxx/944be3a9bace1c3d                             | xxxx                             | application | AVG: 39, MAX: 250, MIN: 2                    |               18.25 |
```

You can also ask for Google's GEMINI suggestions by adding the `-a` parameter.
Just ensure the `GOOGLE_API_KEY` env variable is set.

```bash
...
Checking i-xxxxxxxxxxxxxxxxx
Checking i-xxxxxxxxxxxxxxxxx
...

Querying the GEMINI 1.5 FLASH
* **Rightsize Instances:**  Many instances (e.g., those with "karpenter-main-dev" in the name) could be significantly downsized. The provided data shows substantial potential savings by migrating to `c6g`, `m6g`, or `t4g` instance families.  The savings are clearly indicated in the "future arm" column.  Even if some instances require the higher CPU performance of the x86 options, the `c6a` and `m6a` families offer considerable cost reductions over their `c5` and `m5` counterparts.

* **Stop Unnecessary Instances:** Several instances show periods of inactivity in the "30 days load" column (indicated by "stopped").  These should be stopped permanently if they are no longer needed.  Leaving them running incurs unnecessary costs.  Instances that are only used intermittently should be scheduled to stop and start automatically using EC2 instance scheduling.

* **Utilize Spot Instances:** For non-critical workloads with flexible start times, consider using Spot Instances for significant cost savings.  The cost savings could be substantial for instances with high usage.

* **Enable/Disable Monitoring:** Review the instances with "monitoring" set to "disabled."  While this saves a small amount on monitoring costs, if monitoring data is needed for these instances, enabling it should be prioritized; however, unnecessary monitoring should be disabled to avoid unnecessary charges.

* **Reserved Instances or Savings Plans:** For consistently running instances, explore Reserved Instances (RIs) or Savings Plans to lock in lower prices over a longer term.  The high number of similar "karpenter-main-dev" instances makes this a particularly attractive option.

* **Optimize AMI:** Use the most recent and optimized Amazon Machine Images (AMIs) for your operating system and applications. Older AMIs can be less efficient and lead to higher costs.
```