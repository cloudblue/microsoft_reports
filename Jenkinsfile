pipeline {
    agent {
        label 'docker'
    }
    
	stages {
        stage('Environment Setup') {
            steps {
                sh """
                /opt/rh/rh-python36/root/bin/python3 -m venv venv
                source venv/bin/activate
                pip install --upgrade pip pylint
                python --version
                """
            }
        }
		stage('Test Execution') {
				steps {
					sh """
					touch microsoft-reports.env
					docker-compose run microsoft_reports_extension_test
					"""
				}
        }
        stage('SonarQube Analysis') {
            steps {
                script {
                    def scannerHome = tool name: 'SonarQubeIntZoneScanner', type: 'hudson.plugins.sonar.SonarRunnerInstallation';
                    withSonarQubeEnv('SonarQubeIntZone') {
                        sh """
                        ${scannerHome}/bin/sonar-scanner \
                        -Dsonar.project.tags=connectors \
                        -Dsonar.projectKey=connectors-microsoft-reports \
                        -Dsonar.sources=microsoft-reports/ \
						-Dsonar.tests=tests/ \
                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                        -Dsonar.python.pylint=venv/bin/pylint
                        """
                    }
                }
            }
        }
		stage('push to github'){
			environment { 
					GIT_AUTH = credentials('github-cred') 
				}
			when {
				branch 'master'
				steps{
				sh('''
					git remote add origin https://github.com/cloudblue/microsoft_reports
					git config --local credential.helper "!f() { echo username=\\$GIT_AUTH_USR; echo password=\\$GIT_AUTH_PSW; }; f"
					git checkout master
					git push origin HEAD:master
				''')
				}
			}
		
		}
		stage('Environment Clean') {
            steps {
                sh """
                docker network prune --force --filter until=5m
                """
            }
        }
    }
}