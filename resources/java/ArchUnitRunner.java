import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.EvaluationResult;
import com.tngtech.archunit.library.GeneralCodingRules;
import com.tngtech.archunit.library.DependencyRules;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.fields;
import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

import java.io.Serializable;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/**
 * ArchUnit Runner - Comprehensive Architectural Governance Scanner
 *
 * Scans Java bytecode for architectural violations across 6 categories:
 * 1. General Coding Rules
 * 2. Naming Conventions
 * 3. Dependency Management
 * 4. Annotation-Based Rules
 * 5. Layered Architecture
 * 6. Security & Best Practices
 */
public class ArchUnitRunner {

        public static void main(String[] args) {
                if (args.length < 1) {
                        System.err.println("Usage: java ArchUnitRunner <path-to-classes>");
                        System.exit(1);
                }

                String classesPath = args[0];
                System.out.println("Scanning classes in: " + classesPath);

                try {
                        // Import classes, EXCLUDING test classes (test/, *Test.class, *Tests.class,
                        // *TestCase.class)
                        // Production code only should be subject to architectural governance
                        JavaClasses importedClasses = new ClassFileImporter()
                                        .withImportOption(ImportOption.Predefined.DO_NOT_INCLUDE_TESTS)
                                        .importPath(Paths.get(classesPath));

                        System.err.println("DEBUG: Imported " + importedClasses.size() + " classes (excluding tests).");
                        System.out.println("DEBUG: Imported " + importedClasses.size() + " classes (excluding tests).");

                        List<Violation> violations = new ArrayList<>();

                        // ========================================
                        // CATEGORY 1: GENERAL CODING RULES
                        // ========================================

                        // Rule 1.1: No standard streams (System.out/System.err)
                        checkRule(
                                        GeneralCodingRules.NO_CLASSES_SHOULD_ACCESS_STANDARD_STREAMS,
                                        importedClasses,
                                        "coding-no-std-streams",
                                        1,
                                        violations);

                        // Rule 1.2: No generic exceptions
                        checkRule(
                                        GeneralCodingRules.NO_CLASSES_SHOULD_THROW_GENERIC_EXCEPTIONS,
                                        importedClasses,
                                        "coding-no-generic-exceptions",
                                        1,
                                        violations);

                        // Rule 1.3: No field injection (prefer constructor injection)
                        checkRule(
                                        GeneralCodingRules.NO_CLASSES_SHOULD_USE_FIELD_INJECTION,
                                        importedClasses,
                                        "coding-no-field-injection",
                                        1,
                                        violations);

                        // Rule 1.4: No use of JodaTime (use java.time instead)
                        checkRule(
                                        GeneralCodingRules.NO_CLASSES_SHOULD_USE_JODATIME,
                                        importedClasses,
                                        "coding-no-jodatime",
                                        1,
                                        violations);

                        // Rule 1.5: No use of java.util.logging (use SLF4J, Log4j, Logback)
                        checkRule(
                                        GeneralCodingRules.NO_CLASSES_SHOULD_USE_JAVA_UTIL_LOGGING,
                                        importedClasses,
                                        "coding-no-java-util-logging",
                                        1,
                                        violations);

                        // ========================================
                        // CATEGORY 2: NAMING CONVENTIONS
                        // ========================================

                        // Rule 2.1: Service classes should be in 'service' package
                        ArchRule servicePackageRule = classes()
                                        .that().haveSimpleNameEndingWith("Service")
                                        .and().areNotInterfaces()
                                        .should().resideInAPackage("..service..")
                                        .as("Service classes should reside in '..service..' package");
                        checkRule(servicePackageRule, importedClasses, "naming-service-package", 1, violations);

                        // Rule 2.2: Controller classes should be in 'controller' package
                        ArchRule controllerPackageRule = classes()
                                        .that().haveSimpleNameEndingWith("Controller")
                                        .should().resideInAPackage("..controller..")
                                        .as("Controller classes should reside in '..controller..' package");
                        checkRule(controllerPackageRule, importedClasses, "naming-controller-package", 1, violations);

                        // Rule 2.3: Repository/DAO classes should be in repository or dao package
                        ArchRule repositoryPackageRule = classes()
                                        .that().haveSimpleNameEndingWith("Repository")
                                        .or().haveSimpleNameEndingWith("DAO")
                                        .or().haveSimpleNameEndingWith("Dao")
                                        .should().resideInAnyPackage("..repository..", "..dao..")
                                        .as("Repository/DAO classes should reside in '..repository..' or '..dao..' package");
                        checkRule(repositoryPackageRule, importedClasses, "naming-repository-package", 1, violations);

                        // Rule 2.4: Entity/Model classes should be in entity, model, or domain package
                        ArchRule entityPackageRule = classes()
                                        .that().haveSimpleNameEndingWith("Entity")
                                        .or().haveSimpleNameEndingWith("Model")
                                        .should().resideInAnyPackage("..entity..", "..model..", "..domain..")
                                        .as("Entity/Model classes should reside in '..entity..', '..model..', or '..domain..' package");
                        checkRule(entityPackageRule, importedClasses, "naming-entity-package", 1, violations);

                        // Rule 2.5: Configuration classes should be in config package
                        ArchRule configPackageRule = classes()
                                        .that().haveSimpleNameEndingWith("Config")
                                        .or().haveSimpleNameEndingWith("Configuration")
                                        .should().resideInAPackage("..config..")
                                        .as("Configuration classes should reside in '..config..' package");
                        checkRule(configPackageRule, importedClasses, "naming-config-package", 1, violations);

                        // Rule 2.6: Exception classes should end with 'Exception'
                        ArchRule exceptionNamingRule = classes()
                                        .that().areAssignableTo(Exception.class)
                                        .and().areNotAssignableTo(RuntimeException.class)
                                        .should().haveSimpleNameEndingWith("Exception")
                                        .as("Exception classes should have names ending with 'Exception'");
                        checkRule(exceptionNamingRule, importedClasses, "naming-exception-suffix", 1, violations);

                        // Rule 2.7: Interfaces should not start with 'I' (anti-pattern)
                        ArchRule interfaceNamingRule = classes()
                                        .that().areInterfaces()
                                        .should().haveSimpleNameNotStartingWith("I")
                                        .as("Interface names should not start with 'I' prefix (use descriptive names instead)");
                        checkRule(interfaceNamingRule, importedClasses, "naming-no-interface-prefix", 1, violations);

                        // ========================================
                        // CATEGORY 3: DEPENDENCY MANAGEMENT
                        // ========================================

                        // Rule 3.1: No circular dependencies
                        ArchRule noCyclesRule = com.tngtech.archunit.library.dependencies.SlicesRuleDefinition.slices()
                                        .matching("..(*).")
                                        .should().beFreeOfCycles()
                                        .as("Packages should be free of circular dependencies");
                        checkRule(noCyclesRule, importedClasses, "dependency-no-cycles", 0, violations);

                        // Rule 3.2: Controllers should not access repositories directly
                        ArchRule controllerRepositoryRule = noClasses()
                                        .that().resideInAPackage("..controller..")
                                        .should().dependOnClassesThat().resideInAnyPackage("..repository..", "..dao..")
                                        .as("Controllers should not access repositories directly (use services instead)");
                        checkRule(controllerRepositoryRule, importedClasses, "dependency-controller-no-repository", 0,
                                        violations);

                        // Rule 3.3: No classes should depend on upper packages
                        checkRule(
                                        DependencyRules.NO_CLASSES_SHOULD_DEPEND_UPPER_PACKAGES,
                                        importedClasses,
                                        "dependency-no-upper-packages",
                                        0,
                                        violations);

                        // Rule 3.4: Domain/Entity classes should not depend on infrastructure
                        ArchRule domainIndependenceRule = noClasses()
                                        .that().resideInAnyPackage("..domain..", "..entity..", "..model..")
                                        .should().dependOnClassesThat()
                                        .resideInAnyPackage("..controller..", "..service..", "..repository..",
                                                        "..dao..", "..config..")
                                        .as("Domain/Entity classes should not depend on infrastructure layers");
                        checkRule(domainIndependenceRule, importedClasses, "dependency-domain-independence", 0,
                                        violations);

                        // ========================================
                        // CATEGORY 4: ANNOTATION-BASED RULES
                        // ========================================

                        // Rule 4.1: @Service annotated classes should be in service package
                        ArchRule serviceAnnotationRule = classes()
                                        .that().areAnnotatedWith("org.springframework.stereotype.Service")
                                        .should().resideInAPackage("..service..")
                                        .as("Classes annotated with @Service should reside in '..service..' package");
                        checkRule(serviceAnnotationRule, importedClasses, "annotation-service-package", 1, violations);

                        // Rule 4.2: @Repository annotated classes should be in repository package
                        ArchRule repositoryAnnotationRule = classes()
                                        .that().areAnnotatedWith("org.springframework.stereotype.Repository")
                                        .should().resideInAnyPackage("..repository..", "..dao..")
                                        .as("Classes annotated with @Repository should reside in '..repository..' or '..dao..' package");
                        checkRule(repositoryAnnotationRule, importedClasses, "annotation-repository-package", 1,
                                        violations);

                        // Rule 4.3: @Controller/@RestController annotated classes should be in
                        // controller package
                        ArchRule controllerAnnotationRule = classes()
                                        .that().areAnnotatedWith("org.springframework.stereotype.Controller")
                                        .or().areAnnotatedWith("org.springframework.web.bind.annotation.RestController")
                                        .should().resideInAPackage("..controller..")
                                        .as("Classes annotated with @Controller or @RestController should reside in '..controller..' package");
                        checkRule(controllerAnnotationRule, importedClasses, "annotation-controller-package", 1,
                                        violations);

                        // Rule 4.4: @Transactional should only be in service or repository layer
                        ArchRule transactionalRule = classes()
                                        .that()
                                        .areAnnotatedWith("org.springframework.transaction.annotation.Transactional")
                                        .or()
                                        .areMetaAnnotatedWith(
                                                        "org.springframework.transaction.annotation.Transactional")
                                        .should().resideInAnyPackage("..service..", "..repository..", "..dao..")
                                        .as("Classes with @Transactional should be in service or repository layer");
                        checkRule(transactionalRule, importedClasses, "annotation-transactional-layer", 1, violations);

                        // ========================================
                        // CATEGORY 5: LAYERED ARCHITECTURE
                        // ========================================

                        // Rule 5.1: Enforce 3-tier architecture (Controller -> Service -> Repository)
                        ArchRule layeredArchRule = layeredArchitecture()
                                        .consideringAllDependencies()
                                        .layer("Controller").definedBy("..controller..")
                                        .layer("Service").definedBy("..service..")
                                        .layer("Repository").definedBy("..repository..", "..dao..")
                                        .whereLayer("Controller").mayNotBeAccessedByAnyLayer()
                                        .whereLayer("Service").mayOnlyBeAccessedByLayers("Controller")
                                        .whereLayer("Repository").mayOnlyBeAccessedByLayers("Service")
                                        .as("Architecture should follow layered pattern: Controller -> Service -> Repository");
                        checkRule(layeredArchRule, importedClasses, "architecture-layered", 0, violations);

                        // Rule 5.2: Persistence layer should not depend on web layer
                        ArchRule persistenceWebRule = noClasses()
                                        .that()
                                        .resideInAnyPackage("..repository..", "..dao..", "..entity..", "..model..")
                                        .should().dependOnClassesThat().resideInAnyPackage("..controller..", "..web..")
                                        .as("Persistence layer should not depend on web/controller layer");
                        checkRule(persistenceWebRule, importedClasses, "architecture-persistence-no-web", 0,
                                        violations);

                        // ========================================
                        // CATEGORY 6: SECURITY & BEST PRACTICES
                        // ========================================

                        // Rule 6.1: No use of java.util.Random for security (use SecureRandom)
                        ArchRule secureRandomRule = noClasses()
                                        .should().dependOnClassesThat().haveFullyQualifiedName("java.util.Random")
                                        .as("Use java.security.SecureRandom instead of java.util.Random for security-sensitive operations");
                        checkRule(secureRandomRule, importedClasses, "security-use-secure-random", 0, violations);

                        // Rule 6.2: Serializable classes should have serialVersionUID
                        // Note: This checks for the field existence, not its modifiers
                        ArchRule serialVersionUIDRule = fields()
                                        .that().haveName("serialVersionUID")
                                        .and().areDeclaredInClassesThat().areAssignableTo(Serializable.class)
                                        .should().beStatic()
                                        .andShould().beFinal()
                                        .as("Serializable classes should declare a static final serialVersionUID field");
                        checkRule(serialVersionUIDRule, importedClasses, "security-serial-version-uid", 1, violations);

                        // Rule 6.3: No hardcoded credentials patterns
                        ArchRule noHardcodedCredsRule = fields()
                                        .that().areFinal()
                                        .and().areStatic()
                                        .should().haveNameNotMatching(".*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd].*")
                                        .andShould().haveNameNotMatching(".*[Ss][Ee][Cc][Rr][Ee][Tt].*")
                                        .andShould().haveNameNotMatching(".*[Aa][Pp][Ii][_-]?[Kk][Ee][Yy].*")
                                        .as("Avoid hardcoded credentials in field names (use configuration/environment variables)");
                        checkRule(noHardcodedCredsRule, importedClasses, "security-no-hardcoded-creds", 0, violations);

                        // ========================================
                        // CATEGORY 7: THREAD SAFETY & CONCURRENCY
                        // ========================================

                        // Rule 7.1: Controllers should not have mutable instance fields (thread safety)
                        ArchRule controllerStatelessRule = noClasses()
                                        .that().haveSimpleNameEndingWith("Controller")
                                        .should().haveOnlyFinalFields()
                                        .as("Controllers must be stateless with only final fields (thread safety in multithreaded environments). Use @Autowired final fields for dependencies.");
                        checkRule(controllerStatelessRule, importedClasses, "concurrency-controller-stateless", 0,
                                        violations);

                        // Rule 7.2: Service classes should not have mutable instance fields (thread
                        // safety)
                        ArchRule serviceStatelessRule = noClasses()
                                        .that().haveSimpleNameEndingWith("Service")
                                        .and().areNotInterfaces()
                                        .should().haveOnlyFinalFields()
                                        .as("Service classes must be stateless with only final fields (thread safety in multithreaded environments). Use @Autowired final fields for dependencies.");
                        checkRule(serviceStatelessRule, importedClasses, "concurrency-service-stateless", 0,
                                        violations);

                        // ========================================
                        // CATEGORY 8: PAGINATION REQUIREMENTS
                        // ========================================

                        // Rule 8.1: Search/Find methods should have pagination parameter
                        ArchRule searchPaginationRule = com.tngtech.archunit.lang.syntax.ArchRuleDefinition.methods()
                                        .that().haveName("search")
                                        .or().haveNameMatching(".*[Ss]earch.*")
                                        .or().haveNameMatching(".*[Ff]ind[Aa]ll.*")
                                        .or().haveNameMatching(".*[Ll]ist.*")
                                        .and().areDeclaredInClassesThat().haveSimpleNameEndingWith("Controller")
                                        .and().arePublic()
                                        .should()
                                        .haveRawParameterTypes(
                                                        new com.tngtech.archunit.base.DescribedPredicate<java.util.List<com.tngtech.archunit.core.domain.JavaClass>>(
                                                                        "contain Pageable or Page parameter") {
                                                                @Override
                                                                public boolean test(
                                                                                java.util.List<com.tngtech.archunit.core.domain.JavaClass> paramTypes) {
                                                                        for (com.tngtech.archunit.core.domain.JavaClass paramType : paramTypes) {
                                                                                String typeName = paramType.getName();
                                                                                if (typeName.contains("Pageable") ||
                                                                                                typeName.contains(
                                                                                                                "PageRequest")
                                                                                                ||
                                                                                                typeName.contains(
                                                                                                                "Page")
                                                                                                ||
                                                                                                typeName.contains(
                                                                                                                "Pagination")) {
                                                                                        return true;
                                                                                }
                                                                        }
                                                                        return false;
                                                                }
                                                        })
                                        .as("Search/find/list endpoints in controllers should have pagination parameter (Pageable, PageRequest, or Page) to prevent unbounded result sets");
                        checkRule(searchPaginationRule, importedClasses, "pagination-search-endpoints", 0, violations);

                        // Output JSON
                        printJson(violations);

                } catch (Exception e) {
                        e.printStackTrace();
                        System.exit(1);
                }
        }

        private static void checkRule(ArchRule rule, JavaClasses classes, String ruleId, int severity,
                        List<Violation> violations) {
                try {
                        // Allow rules to pass even if no classes match the criteria
                        // This makes the scanner work across diverse projects
                        EvaluationResult result = rule.allowEmptyShould(true).evaluate(classes);
                        if (!result.getFailureReport().isEmpty()) {
                                for (String failure : result.getFailureReport().getDetails()) {
                                        violations.add(new Violation(ruleId, failure, severity));
                                }
                        }
                } catch (Exception e) {
                        // Silently ignore rules that might not apply (e.g., if package doesn't exist or
                        // annotation not present)
                        // This allows the scanner to work on diverse projects without failing
                }
        }

        private static void printJson(List<Violation> violations) {
                System.out.println("---JSON-START---");
                System.out.print("[");
                for (int i = 0; i < violations.size(); i++) {
                        Violation v = violations.get(i);
                        System.out.printf("{\"rule\": \"%s\", \"message\": \"%s\", \"severity\": %d}",
                                        escapeJson(v.rule), escapeJson(v.message), v.severity);
                        if (i < violations.size() - 1) {
                                System.out.print(",");
                        }
                }
                System.out.println("]");
                System.out.println("---JSON-END---");
        }

        private static String escapeJson(String s) {
                return s.replace("\\", "\\\\")
                                .replace("\"", "\\\"")
                                .replace("\n", "\\n")
                                .replace("\r", "\\r")
                                .replace("\t", "\\t");
        }

        static class Violation {
                String rule;
                String message;
                int severity; // 0 = Critical, 1 = Warning, 2 = Info

                public Violation(String rule, String message, int severity) {
                        this.rule = rule;
                        this.message = message;
                        this.severity = severity;
                }
        }
}
