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
					touch .microsoft_reports_extension_dev.env
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
                        -Dsonar.sources=reports/ \
						-Dsonar.tests=tests/ \
                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                        -Dsonar.python.pylint=venv/bin/pylint
                        """
                    }
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